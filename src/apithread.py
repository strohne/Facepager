import queue
import collections
import threading
import time
from copy import deepcopy
from utilities import *

class ApiThreadPool():
    def __init__(self, module):
        self.input = collections.deque()
        self.errors = queue.Queue()
        self.output = queue.Queue(100)
        self.logs = queue.Queue()
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
        except queue.Empty as e:
            msg = None
        finally:
            return msg

    # Jobs
    def addJob(self, job):
        if job is not None:
            job['number'] = self.jobcount
            self.jobcount += 1
        self.input.append(job)

    def applyJobs(self):
        self.jobsadded = True
        if not self.jobcount:
            self.stopJobs()

    def getJob(self):
        try:
            if self.output.empty():
                raise queue.Empty()

            job = self.output.get(True, 1)
            self.output.task_done()
        except queue.Empty as e:
            job = {'waiting': True}
        finally:
            return job

    def suspendJobs(self):
        self.suspended = True
        for thread in self.threads:
            thread.process.clear()

    def resumeJobs(self):
        for thread in self.threads:
            thread.process.set()

        self.spawnThreads()
        self.suspended = False

    def stopJobs(self):
        for thread in self.threads:
            thread.halt.set()
            thread.process.set()

        self.module.disconnectSocket()

    def clearJobs(self):
        self.input.clear()

    def getJobCount(self):
        return len(self.input)

    def getOutputCount(self):
        return self.output.qsize()

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

    # Errors
    def addError(self, job):
        newjob = {'nodeindex': job['nodeindex'],
                  'nodedata': deepcopy(job['nodedata']),
                  'options': deepcopy(job['options'])}
        self.errors.put(newjob)

    def retryJobs(self):
        while not self.errors.empty():
            newjob = self.errors.get()
            #if newjob['options'].get('ratelimit', False):
            newjob['number'] = self.jobcount
            self.jobcount += 1
            self.input.appendleft(newjob)

        self.resumeJobs()

    def clearRetry(self):
        with self.errors.mutex:
            self.errors.queue.clear()

    def getErrorJobsCount(self):
        return self.errors.qsize()

    def hasErrorJobs(self):
        return not self.errors.empty()

    # Threads
    def addThread(self):
        thread = ApiThread(self.input, self.errors, self.output, self.module, self, self.logs, self.threadcount+1)
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

        threadcount = min(len(self.input), self.maxthreads)
        threadcount = max(1, threadcount)

        self.setThreadCount(threadcount)

    def threadFinished(self):
        with self.pool_lock:
            self.threadcount -= 1
            if (self.threadcount == 0):
                self.clearJobs()
                self.output.put(None)  #sentinel

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
    def __init__(self, input, retry, output, module, pool, logs, number):
        threading.Thread.__init__(self)
        #self.daemon = True
        self.pool = pool
        self.input = input
        self.retry = retry
        self.output = output
        self.module = module
        self.logs = logs
        self.number = number
        self.halt = threading.Event()
        self.retry = threading.Event()
        self.process = threading.Event()

    def run(self):
        def logData(data, options, headers):
            data = sliceData(data, headers, options)
            out = {'nodeindex': job['nodeindex'], 'nodedata' : job['nodedata'], 'data': data, 'options': options}
            self.output.put(out)

        def logMessage(msg):
            self.logs.put(msg)

        def logProgress(progress):
            progress['progress'] = job.get('number', 0)
            progress['threadnumber'] = job.get('threadnumber', 0)
            self.output.put(progress)
            if self.halt.isSet():
                raise CancelException('Request cancelled.')
            
        try:
            while not self.halt.isSet():
                try:
                    time.sleep(0)

                    # Get from input queue
                    job = self.input.popleft()
                    job['threadnumber'] = self.number

                    # Fetch data
                    try:
                        self.module.fetchData(job['nodedata'], job['options'], logData, logMessage, logProgress)
                    finally:
                        # Progress
                        self.output.put({'progress': job.get('number', 0), 'threadnumber': self.number})


                # queue empty
                except IndexError:
                    pass

                # canceled
                except CancelException:
                    pass

                # error
                except Exception as e:
                    logMessage(e)


                # wait for signal
                self.process.clear()
                self.process.wait()
        finally:
            self.pool.threadFinished()

class CancelException(Exception):
    pass