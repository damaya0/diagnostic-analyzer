from datetime import datetime
import re

DATE_REGEX = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})$")

class Analysis:
    def __init__(self, id, name, config, thread_groups_config):
        self.id = id
        self.name = name
        self.date = None
        self.dateString = None
        self.filename = None
        self.config = config
        self.thread_groups_config = thread_groups_config
        self.threadComparator = Thread.compare
        self._init()
        self.synchronizers = []

    def analyze(self, text):
        self._init()
        self._analyzeThreads(text)
        self._countRunningMethods()
        self._analyzeSynchronizers()
        self._analyzeDeadlocks()
        # must sort after deadlock detection
        # self.synchronizers.sort(key=lambda x: x.compare())

    def _init(self):
        self.threads = []
        self.threadMap = {}
        self.threadsByStatus = {}
        self.synchronizers = []
        self.synchronizerMap = {}
        self.ignoredData = Util.StringCounter()
        self.runningMethods = Util.StringCounter()
        self.deadlockStatus = DeadlockStatus.NONE
        self.threadGroupsConfig = self.thread_groups_config

    def _analyzeThreads(self, text):
        self._currentThread = None
        lines = text.split('\n')
        for i in range(len(lines)):
            line = lines[i]
            if self.date is None and DATE_REGEX.match(line.strip()):
                ln = line.strip()
                dt = DATE_REGEX.match(ln)
                if dt is not None:
                    self.date = datetime(int(dt.group(1)), int(dt.group(2)), int(dt.group(3)), int(dt.group(4)), int(dt.group(5)), int(dt.group(6)))
                    self.dateString = ln
                    continue

            while self._isIncompleteThreadHeader(line):
                # Multi line thread name
                i += 1
                if i >= len(lines):
                    break

                # Replace thread name newline with ", "
                line += ', ' + lines[i]

            self._handleLine(line)

        if self._currentThread:
            del self._currentThread

        self._identifyWaitedForSynchronizers()
        self._mapThreadsByStatus()

    def _isIncompleteThreadHeader(self, line):
        if line:  # Check if the line is not empty
            if line[0] != '"':
            # Thread headers start with ", this is not it 
                return False
        else:
            return False
        #possible error. check this if code misses 
        if 'prio=' in line:
            # Thread header contains "prio=" => we think it's complete 
            return False
        if 'Thread t@' in line:
            # Thread header contains a thread ID => we think it's complete 
            return False
        if line[-2:] == '":':
            return False
        return True

    def _handleLine(self, line):
        # TODO better way of new thread detection than creating a new object
        thread = Thread(line)
        if thread.isValid():
            self.threads.append(thread)
            self.threadMap[thread.tid] = thread
            self._currentThread = thread
            return
        elif re.match(r'^\s*$', line):
            # We ignore empty lines, and lines containing only whitespace
            return
        elif self._currentThread is not None:
            if self._currentThread.addStackLine(line):
                return

        self.ignoredData.add_string(line)

    def _identifyWaitedForSynchronizers(self):
        for thread in self.threads:
            if thread.threadState not in ['TIMED_WAITING (on object monitor)', 'WAITING (on object monitor)']:
                # Not waiting for notification
                continue
            if thread.wantNotificationOn is not None or thread.classicalLockHeld is None:
                continue

            thread.setWantNotificationOn(thread.classicalLockHeld)

    def _groupThreadsByPool(self):
        pools = {}

        # Populate pools from threadGroupsConfig
        for group in self.threadGroupsConfig['threadGroups']:
            pools[group['poolName']] = []

        pools['Threads with no pools'] = []

        for thread in self.threads:
            grouped = False
            for poolName in pools:
                if poolName != 'Threads with no pools' and poolName in thread.name:
                    pools[poolName].append(thread)
                    grouped = True
                    break
            if not grouped:
                pools['Threads with no pools'].append(thread)

        self.threadsByPool = pools

    def _mapThreadsByStatus(self):
        self._groupThreadsByPool()
        for poolName, poolThreads in self.threadsByPool.items():
            for thread in poolThreads:
                status = thread.getStatus().status
                if status in self.threadsByStatus:
                    self.threadsByStatus[status].append(thread)
                else:
                    self.threadsByStatus[status] = [thread]

    def _countRunningMethods(self):
        for thread in self.threads:
            if not thread.getStatus().isRunning() or len(thread.frames) == 0:
                continue
            runningMethod = re.sub(r'^\s+at\s+', '', thread.frames[0])
            self.runningMethods.add_string(runningMethod, thread)
        self.runningMethods.sort_sources(self.threadComparator)

    def _analyzeSynchronizers(self):
        self._mapSynchronizers()
        self._xrefSynchronizers()
        self._sortSynchronizersRefs()

    def _mapSynchronizers(self):
        for thread in self.threads:
            self._registerSynchronizer(thread.wantNotificationOn, thread.synchronizerClasses)
            self._registerSynchronizer(thread.wantToAcquire, thread.synchronizerClasses)

            for lock in thread.locksHeld:
                self._registerSynchronizer(lock, thread.synchronizerClasses)

        ids = list(self.synchronizerMap.keys())
        for id in ids:
            self.synchronizers.append(self.synchronizerMap[id])

    def _registerSynchronizer(self, id, synchronizerClasses):
        if id is None:
            return
        if id not in self.synchronizerMap:
            self.synchronizerMap[id] = Synchronizer(id, synchronizerClasses.get(id))

    def _xrefSynchronizers(self):
        for thread in self.threads:
            if thread.wantNotificationOn is not None:
                synchronizer = self.synchronizerMap[thread.wantNotificationOn]
                synchronizer.notificationWaiters.append(thread)
            if thread.wantToAcquire is not None:
                synchronizer = self.synchronizerMap[thread.wantToAcquire]
                synchronizer.lockWaiters.append(thread)

            for lock in thread.locksHeld:
                synchronizer = self.synchronizerMap[lock]
                synchronizer.lockHolder = thread

    def _sortSynchronizersRefs(self):
        for synchronizer in self.synchronizers:
            # synchronizer.lockWaiters.sort(key=self.threadComparator)
            # synchronizer.notificationWaiters.sort(key=self.threadComparator)
            #possible error
            pass

    def _analyzeDeadlocks(self):
        for synchronizer in self.synchronizers:
            status = self._determineDeadlockStatus(synchronizer)
            if status.severity == 0:
                continue
            if self.deadlockStatus['severity'] < status['severity']:
                self.deadlockStatus = status
            synchronizer.deadlockStatus = status

    def _determineDeadlockStatus(self, sync):
        if sync.lockHolder is None:
            if len(sync.lockWaiters) > 0:
                return DeadlockStatus(DeadlockStatus.DEADLOCKED, [])
            else:
                return DeadlockStatus.NONE
        if sync.lockHolder.getStatus().status == "WAITING_NOTIFY" and sync.lockHolder.wantNotificationOn is None:
            return DeadlockStatus(DeadlockStatus.HIGH_RISK, [], 'Waiting for notification on unknown object.')
        if not sync.lockHolder.getStatus().isWaiting():
            return DeadlockStatus.NONE
        if len(sync.lockWaiters) == 0 and len(sync.notificationWaiters) == 0:
            return DeadlockStatus.NONE
        
        work = []
        work.append(sync.lockHolder)
        visited = {sync.id: True}
        while len(work) > 0:
            thread = work.pop()
            if thread.wantNotificationOn is not None:
                return DeadlockStatus(DeadlockStatus.HIGH_RISK, [])
            if thread.wantToAcquire is not None:
                if thread.wantToAcquire in visited:
                    return DeadlockStatus(DeadlockStatus.DEADLOCKED, [])
                visited[thread.wantToAcquire] = True
                synchro = self.synchronizerMap[thread.wantToAcquire]
                if synchro.lockHolder is not None:
                    work.append(synchro.lockHolder)
        
        return DeadlockStatus(DeadlockStatus.DEADLOCKED, [])


class Thread:
    def __init__(self, spec):
        self.spec = spec
        self.threadState = None
        self.wantNotificationOn = None
        self.classicalLockHeld = None
        self.name = None
        self.tid = None  # Assuming tid is set elsewhere
        self.frames = []
        self.synchronizerClasses = {}
        self.wantToAcquire = None
        self.locksHeld = []
        self.prio = None
        self.osPrio = None
        self.daemon = False
        self.number = None
        self.group = None
        self.state = None
        self.dontKnow = None
        
        # Initialize the object
        self._parseSpec(spec)

        self.frames = []
        self.wantNotificationOn = None
        self.wantToAcquire = None
        self.locksHeld = []
        self.synchronizerClasses = {}
        self.threadState = None
        self.classicalLockHeld = None

    def isValid(self):
        return hasattr(self, 'name') and self.name is not None

    def addStackLine(self, line):
        FRAME = re.compile(r'^\s+at (.*)')
        match = FRAME.match(line)
        if match:
            self.frames.append(match.group(1))
            return True

        THREAD_STATE = re.compile(r'^\s*java.lang.Thread.State: (.*)')
        match = THREAD_STATE.match(line)
        if match:
            self.threadState = match.group(1)
            return True

        SYNCHRONIZATION_STATUS = re.compile(r'^\s+- (.*?) +<([x0-9a-f]+)> \(a (.*)\)')
        match = SYNCHRONIZATION_STATUS.match(line)
        if match:
            state = match.group(1)
            id = match.group(2)
            className = match.group(3)
            self.synchronizerClasses[id] = className

            if state == "eliminated":
                return True  # JVM internal optimization, not sure why it's in the thread dump at all
            elif state in ["waiting on", "parking to wait for"]:
                self.wantNotificationOn = id
                return True
            elif state == "waiting to lock":
                self.wantToAcquire = id
                return True
            elif state == "locked":
                if self.wantNotificationOn == id:
                    return True  # Lock is released while waiting for the notification
                # self._arrayAddUnique(self.locksHeld, id)
                Util.array_add_unique(self.locksHeld, id)
                if (len(self.frames) >= 2 and self.classicalLockHeld is None and
                    'java.lang.Object.wait' in self.frames[-2]):
                    self.classicalLockHeld = id
                return True
            else:
                return False

        HELD_LOCK = re.compile(r'^\s+- <([x0-9a-f]+)> \(a (.*)\)')
        match = HELD_LOCK.match(line)
        if match:
            lockId = match.group(1)
            lockClassName = match.group(2)
            self.synchronizerClasses[lockId] = lockClassName
            Util.array_add_unique(self.locksHeld, lockId)
            # self._arrayAddUnique(self.locksHeld, lockId)
            return True

        LOCKED_OWNABLE_SYNCHRONIZERS = re.compile(r'^\s+Locked ownable synchronizers:')
        match = LOCKED_OWNABLE_SYNCHRONIZERS.match(line)
        if match:
            return True  # Ignore these lines

        NONE_HELD = re.compile(r'^\s+- None')
        match = NONE_HELD.match(line)
        if match:
            return True  # Ignore these lines

        return False

    def setWantNotificationOn(self, lockId):
        self.wantNotificationOn = lockId

        if lockId in self.locksHeld:
            self.locksHeld.remove(lockId)

        if self.classicalLockHeld == lockId:
            self.classicalLockHeld = None

    def getStatus(self):
        # TODO: do not recreate every time
        return ThreadStatus(self)

    def _parseSpec(self, line):
        def extract(pattern, line):
            match = re.search(pattern, line)
            if match:
                return match.group(1), line[:match.start()] + line[match.end():]
            return None, line

        self.dontKnow, line = extract(r'\[([0-9a-fx,]+)\]$', line)
        self.nid, line = extract(r' nid=([0-9a-fx,]+)', line)
        self.tid, line = extract(r' tid=([0-9a-fx,]+)', line)
        
        if self.tid is None:
            self.tid, line = extract(r' - Thread t@([0-9a-fx]+)', line)

        self.prio, line = extract(r' prio=([0-9]+)', line)
        self.osPrio, line = extract(r' os_prio=([0-9a-fx,]+)', line)
        daemon, line = extract(r' (daemon)', line)
        self.daemon = daemon is not None
        self.number, line = extract(r' #([0-9]+)', line)
        self.group, line = extract(r' group="(.*)"', line)
        self.name, line = extract(r'^"(.*)" ', line)

        if self.name is None:
            self.name, line = extract(r'^"(.*)":?$', line)

        self.state = line.strip()

        if self.name is None:
            return None
        if self.tid is None:
            self.tid = "generated-id-" + str(Thread._internal_generated_id_counter)
            Thread._internal_generated_id_counter += 1

    @staticmethod
    def compare(a, b):
        res = (a.name > b.name) - (a.name < b.name)
        if res != 0:
            return res
        return (a.tid > b.tid) - (a.tid < b.tid)
    
class ThreadStatus:
    def __init__(self, thread):
        self.thread = thread
        self.status = None
        self.determineStatus()

    def isRunning(self):
        return self.status == ThreadStatus.RUNNING

    def isWaiting(self):
        return self.status in [ThreadStatus.WAITING_ACQUIRE, 
                               ThreadStatus.WAITING_NOTIFY, 
                               ThreadStatus.WAITING_NOTIFY_TIMED]

    def determineStatus(self):
        if self.thread.wantNotificationOn is not None:
            self.status = ThreadStatus.WAITING_NOTIFY
        elif self.thread.threadState == 'WAITING (on object monitor)':
            self.status = ThreadStatus.WAITING_NOTIFY
        elif self.thread.threadState == 'TIMED_WAITING (on object monitor)':
            self.status = ThreadStatus.WAITING_NOTIFY_TIMED
        elif self.thread.wantToAcquire is not None:
            self.status = ThreadStatus.WAITING_ACQUIRE
        elif self.thread.threadState == 'TIMED_WAITING (sleeping)':
            self.status = ThreadStatus.SLEEPING
        elif self.thread.threadState == 'NEW':
            self.status = ThreadStatus.NEW
        elif self.thread.threadState == 'TERMINATED':
            self.status = ThreadStatus.TERMINATED
        elif self.thread.threadState == 'WAITING (parking)':
            self.status = ThreadStatus.WAITING_NOTIFY
        elif self.thread.threadState == 'TIMED_WAITING (parking)':
            self.status = ThreadStatus.WAITING_NOTIFY_TIMED
        elif self.thread.threadState == 'BLOCKED (on object monitor)':
            self.status = ThreadStatus.WAITING_ACQUIRE
        elif len(self.thread.frames) == 0:
            self.status = ThreadStatus.NON_JAVA_THREAD
        elif self.thread.threadState == 'RUNNABLE':
            self.status = ThreadStatus.RUNNING
        elif self.thread.threadState is None:
            self.determineStatusStateless()
        else:
            self.status = ThreadStatus.UNKNOWN

    def determineStatusStateless(self):
        if self.thread.state == 'RUNNABLE':
            self.status = ThreadStatus.RUNNING
        elif self.thread.state == 'TIMED_WAITING':
            self.status = ThreadStatus.WAITING_NOTIFY_TIMED
        elif self.thread.state == 'WAITING':
            self.status = ThreadStatus.WAITING_NOTIFY
        elif self.thread.state == 'NEW':
            self.status = ThreadStatus.NEW
        elif self.thread.state == 'TERMINATED':
            self.status = ThreadStatus.TERMINATED
        elif self.thread.state == 'BLOCKED':
            self.status = ThreadStatus.WAITING_ACQUIRE
        else:
            self.status = ThreadStatus.NON_JAVA_THREAD

    def __str__(self):
        return self.status

# Constants for ThreadStatus
ThreadStatus.UNKNOWN = "?unknown?"
ThreadStatus.RUNNING = "running"
ThreadStatus.NON_JAVA_THREAD = "non-Java thread"
ThreadStatus.TERMINATED = "terminated"
ThreadStatus.NEW = "not started"
ThreadStatus.SLEEPING = "sleeping"
ThreadStatus.WAITING_ACQUIRE = "waiting to acquire"
ThreadStatus.WAITING_NOTIFY = "awaiting notification"
ThreadStatus.WAITING_NOTIFY_TIMED = "awaiting notification (timed)"

ThreadStatus.ALL = [
    ThreadStatus.RUNNING,
    ThreadStatus.WAITING_NOTIFY,
    ThreadStatus.WAITING_NOTIFY_TIMED,
    ThreadStatus.WAITING_ACQUIRE,
    ThreadStatus.SLEEPING,
    ThreadStatus.NEW,
    ThreadStatus.TERMINATED,
    ThreadStatus.NON_JAVA_THREAD,
    ThreadStatus.UNKNOWN
]

class DeadlockStatus:
    NO_RISK = 0
    LOW_RISK = 1
    HIGH_RISK = 2
    DEADLOCKED = 3

    NONE = None  # This will be initialized after the class definition

    def __init__(self, severity, trail=None, detail=None):
        self.severity = severity
        self.detail = detail
        self.trail = trail or []

    def __str__(self):
        if self.severity == DeadlockStatus.NO_RISK:
            return "No deadlock"
        elif self.severity == DeadlockStatus.LOW_RISK:
            return "Deadlock suspect"
        elif self.severity == DeadlockStatus.HIGH_RISK:
            return "Possible deadlock"
        elif self.severity == DeadlockStatus.DEADLOCKED:
            return "Deadlocked"
        else:
            return "Unknown?"

    def notificationLevel(self):
        if self.severity == DeadlockStatus.NO_RISK:
            return ""
        elif self.severity == DeadlockStatus.LOW_RISK:
            return "info"
        elif self.severity == DeadlockStatus.HIGH_RISK:
            return "warning"
        elif self.severity == DeadlockStatus.DEADLOCKED:
            return "danger"
        else:
            return "default"

# Initializing the NONE constant
DeadlockStatus.NONE = DeadlockStatus(DeadlockStatus.NO_RISK, [])

class Synchronizer:
    def __init__(self, id, className):
        self.id = id
        self.className = className
        self.notificationWaiters = []
        self.lockWaiters = []
        self.lockHolder = None
        self.deadlockStatus = DeadlockStatus.NONE

    def getThreadCount(self):
        count = 0
        if self.lockHolder is not None:
            count += 1
        count += len(self.lockWaiters)
        count += len(self.notificationWaiters)
        return count

    @staticmethod
    def compare(a, b):
        deadlock = b.deadlockStatus.severity - a.deadlockStatus.severity
        if deadlock != 0:
            return deadlock

        count_diff = b.getThreadCount() - a.getThreadCount()
        if count_diff != 0:
            return count_diff

        pretty_a = Util.get_pretty_class_name(a.className)
        pretty_b = Util.get_pretty_class_name(b.className)
        if pretty_a != pretty_b:
            return (pretty_a > pretty_b) - (pretty_a < pretty_b)

        return (a.id > b.id) - (a.id < b.id)

class Util:
    @staticmethod
    def get_pretty_class_name(class_name):
        if class_name is None:
            return None

        class_for_pattern = re.compile(r'^java.lang.Class for .*\.([^.]*)$')
        match = class_for_pattern.match(class_name)
        if match:
            return f"{match.group(1)}.class"

        package_pattern = re.compile(r'^.*\.([^.]*)$')
        match = package_pattern.match(class_name)
        if match:
            return match.group(1)

        return class_name

    @staticmethod
    def array_add_unique(array, to_add):
        if to_add not in array:
            array.append(to_add)

    @staticmethod
    def extract(regex, string):
        match = re.search(regex, string)
        if match is None:
            return {
                "value": None,
                "shorterString": string
            }
        return {
            "value": match.group(1),
            "shorterString": string.replace(match.group(0), "")
        }

    @staticmethod
    def arrays_equal(a, b):
        if len(a) != len(b):
            return False
        return all(e == b[idx] for idx, e in enumerate(a))

    class StringCounter:
        def __init__(self):
            self._strings_to_counts = {}
            self.length = 0

        def add_string(self, string, source=None):
            if string not in self._strings_to_counts:
                self._strings_to_counts[string] = {
                    "count": 0,
                    "sources": []
                }
            self._strings_to_counts[string]["count"] += 1
            self._strings_to_counts[string]["sources"].append(source)
            self.length += 1

        def has_string(self, string):
            return string in self._strings_to_counts

        def get_strings(self):
            return_me = []
            for string, data in self._strings_to_counts.items():
                return_me.append({
                    "count": data["count"],
                    "string": string,
                    "sources": data["sources"]
                })
            return_me.sort(key=lambda x: (-x["count"], x["string"]))
            return return_me

        def __str__(self):
            counted_strings = self.get_strings()
            return "\n".join(f"{item['count']} {item['string']}" for item in counted_strings)

        def sort_sources(self, compare=None):
            if compare is None:
                return
            for data in self._strings_to_counts.values():
                #data["sources"].sort(key=compare)
                #possible error
                pass
