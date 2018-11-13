import Queue
import collections
import threading
import time
from copy import deepcopy

class ApiThreadPool():
    def __init__(self, module):
        self.input = collections.deque()
        self.errors = Queue.Queue()
        self.output = Queue.Queue(100)
        self.logs = Queue.Queue()
        self.module = module
        self.threads = []
        self.pool_lock = threading.Lock()
        self.threadcount = 0
        self.maxthreads = 1
        self.jobcount = 0
        self.jobsadded = False
        self.suspended = False

    def getLogMessage(self):
        try:
            if self.logs.empty():
                msg = None
            else:
                msg = self.logs.get(True, 1)
                self.logs.task_done()
        except Queue.Empty as e:
            msg = None
        finally:
            return msg

    def addError(self, job):
        newjob = {'nodeindex': job['nodeindex'],
                  'nodedata': deepcopy(job['nodedata']),
                  'options': deepcopy(job['options'])}
        self.errors.put(newjob)

    def clearRetry(self):
        with self.errors.mutex:
            self.errors.queue.clear()

    def addJob(self, job):
        if job is not None:
            job['number'] = self.jobcount
            self.jobcount += 1
        self.input.append(job)

        if (self.jobcount % 10 == 0) and not self.suspended:
            self.resumeJobs()

    def retryJobs(self):
        while not self.errors.empty():
            newjob = self.errors.get()
            newjob['number'] = self.jobcount
            self.jobcount += 1
            self.input.appendleft(newjob)

        self.resumeJobs()

    def clearJobs(self):
        self.input.clear()

    def getJob(self):
        try:
            if self.output.empty():
                raise Queue.Empty()

            job = self.output.get(True, 1)
            self.output.task_done()
        except Queue.Empty as e:
            job = {'waiting': True}
        finally:
            return job

    def applyJobs(self):
        self.jobsadded = True

        if not self.suspended:
            self.resumeJobs()

#        self.resumeJobs()
        # with self.pool_lock:
        #     for x in range(0,self.threadcount):
        #         pass
                #self.addJob(None)  # sentinel empty job

    def hasJobs(self):
        if not self.jobsadded:
            return True

        if self.suspended:
            return True

        if len(self.input) > 0:
            return True

        if not self.output.empty():
            return True

        for thread in self.threads:
            if thread.process.isSet():
                return True

        return False

    def addThread(self):
        thread = ApiThread(self.input, self.errors, self.output, self.module, self, self.logs)
        self.threadcount += 1
        self.threads.append(thread)

        thread.start()
        thread.process.set()


    def removeThread(self):
        if count(self.threads):
            self.threads[0].halt.set()
            self.threads[0].process.set()

    def spawnThreads(self, threadcount= None):
        if threadcount is not None:
            self.maxthreads = threadcount

        if len(self.input) > 50:
            threadcount = min(5,self.maxthreads)
        elif len(self.input) > 10:
            threadcount = min(1,self.maxthreads)
        else:
            threadcount = 1

        self.setThreadCount(threadcount)

    def stopJobs(self):
        for thread in self.threads:
            thread.halt.set()
            thread.process.set()

        self.module.disconnectSocket()

    def suspendJobs(self):
        self.suspended = True
        for thread in self.threads:
            thread.process.clear()

    def resumeJobs(self):
        for thread in self.threads:
            thread.process.set()

        self.spawnThreads()
        self.suspended = False


    def threadFinished(self):
        with self.pool_lock:
            self.threadcount -= 1
            if (self.threadcount == 0):
                self.clearJobs()
                self.output.put(None)  #sentinel

    def getJobCount(self):
        return len(self.input)

    def getTotalCount(self):
        return self.jobcount

    def getThreadCount(self):
        with self.pool_lock:
            return self.threadcount

    def setThreadCount(self,threadcount):
        with self.pool_lock:
            diff = threadcount - self.threadcount
            if diff > 0:
                for x in range(diff):
                    self.addThread()
            elif diff < 0:
                for x in range(diff):
                    self.removeThread()

# Thread will process jobs and automatically pause if no job is available.
# To resume after adding new jobs set process-Signal.
# To completely halt the tread, set halt-Signal and process-Signal.
class ApiThread(threading.Thread):
    def __init__(self, input, retry, output, module, pool, logs):
        threading.Thread.__init__(self)
        #self.daemon = True
        self.pool = pool
        self.input = input
        self.retry = retry
        self.output = output
        self.module = module
        self.logs = logs
        self.halt = threading.Event()
        self.retry = threading.Event()
        self.process = threading.Event()

    def run(self):
        def streamingData(data, options, headers, streamingTab=False):
            out = {'nodeindex': job['nodeindex'], 'nodedata' : job['nodedata'], 'data': data, 'options': options, 'headers': headers}
            if streamingTab:
                out["streamprogress"] = True
            self.output.put(out)

        def logMessage(msg):
            self.logs.put(msg)

        def logProgress(current=0, total=0):
            self.output.put({'progress': job.get('number', 0),'current':current,'total':total})
            if self.halt.set():
                raise CancelledError('Request cancelled.')
            
        try:
            while not self.halt.isSet():
                try:
                    time.sleep(0)

                    # Get from input queue
                    try:
                        job = self.input.popleft()
                    except:
                        self.process.clear()
                        job = None

                    # Process job
                    if job is not None:
                        self.module.fetchData(job['nodedata'], job['options'], streamingData,logMessage,logProgress)

                    if job is not None:
                        self.output.put({'progress': job.get('number', 0)})
                except Exception as e:
                    logMessage(e)

                self.process.wait()
        finally:
            self.pool.threadFinished()