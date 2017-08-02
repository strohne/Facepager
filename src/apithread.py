import Queue
import threading
import time


class ApiThreadPool():
    def __init__(self, module):
        self.input = Queue.Queue()
        self.output = Queue.Queue(100)
        self.logs= Queue.Queue()
        self.module = module
        self.threads = []
        self.pool_lock = threading.Lock()
        self.threadcount = 0
        self.jobcount = 0

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

    def addJob(self, job):
        if job is not None:
            job['number'] = self.jobcount
            self.jobcount += 1
        self.input.put(job)

    def getJob(self):
        try:
            if self.output.empty():
                job = {'waiting': True}
            else:
                job = self.output.get(True, 1)
                self.output.task_done()
        except Queue.Empty as e:
            job = {'waiting': True}
        finally:
            return job

    def closeJobs(self):
        with self.pool_lock:
            for x in range(0,self.threadcount):
                self.addJob(None)  # sentinel empty job

    def processJobs(self,threadcount=None):
        with self.pool_lock:
            if threadcount is not None:
                maxthreads = threadcount
            elif self.input.qsize() > 50:
                maxthreads = 5
            elif self.input.qsize() > 10:
                maxthreads = 2
            else:
                maxthreads = 1

            self.threads = []
            for x in range(maxthreads):
                self.addThread()

    def addThread(self):
        #self.addJob(None)  # sentinel empty job
        thread = ApiThread(self.input, self.output, self.module, self,self.logs)
        self.threadcount += 1
        self.threads.append(thread)
        thread.start()

    def removeThread(self):
        if count(self.threads):
            self.threads[0].halt.set()

    def stopJobs(self):
        for thread in self.threads:
            thread.halt.set()
        self.module.disconnectSocket()

    def threadFinished(self):
        with self.pool_lock:
            self.threadcount -= 1
            if (self.threadcount == 0):
                with self.input.mutex:
                    self.input.queue.clear()
                self.output.put(None)  #sentinel

    def getJobCount(self):
        return len(self.input)

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


class ApiThread(threading.Thread):
    def __init__(self, input, output, module, pool,logs):
        threading.Thread.__init__(self)
        #self.daemon = True
        self.pool = pool
        self.input = input
        self.output = output
        self.module = module
        self.logs = logs
        self.halt = threading.Event()

    def run(self):
        def streamingData(data, options, headers, streamingTab=False):
            out = {'nodeindex': job['nodeindex'], 'data': data, 'options': options, 'headers': headers}
            if streamingTab:
                out["streamprogress"] = True
            self.output.put(out)

        def logMessage(msg):
            self.logs.put(msg)

        try:
            while not self.halt.isSet():
                try:
                    time.sleep(0)
                    job = self.input.get()
                    try:
                        if job is None:
                            self.halt.set()
                        else:
                            self.module.fetchData(job['data'], job['options'], streamingData,logMessage)
                    finally:
                        self.input.task_done()
                        if job is not None:
                            self.output.put({'progress': job.get('number', 0)})
                except Exception as e:
                    logmessage(e)
        finally:
            self.pool.threadFinished()