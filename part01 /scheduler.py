# =========================================================
# scheduler.py  – Pure simulation logic (no pygame)
# =========================================================
import random


class Job:
    def __init__(self, job_id, bursts, arrival_time=0, quantum=4):
        self.id = job_id
        self.bursts = bursts  # e.g., [5, 3, 2]
        self.quantum = quantum # use the existing time quantum
        self.arrival_time = arrival_time
        self.current_burst = 0
        self.state = "ready" # "new"

    def __repr__(self):
        return f"P{self.id}"


class Scheduler:
    def __init__(self, jobs):
        self.clock = 0
        self.ready = []  
        self.wait = []
        self.cpu = []
        self.io = []
        # jobs are sorted by their arrival times in ascending order, and
        # puts these jobs in a new list called waiting_arrivals.
        self.waiting_arrivals = sorted(jobs, key=lambda j: j.arrival_time)    

    # -----------------------------------------------------
    # Creates and holds a list of arrived jobs according to
    # its tick. Method loops through waiting jobs, and will 
    # move said job(s) to the ready queue. 
    # -----------------------------------------------------
    def check_arrivals(self):
        arrived = []
        for job in list(self.waiting_arrivals):
            if self.clock == job.arrival_time:
                job.state = "ready"
                self.ready.append(job)
                arrived.append(job)
    
    # remove arrived jobs from waiting list
        for job in arrived:
            self.waiting_arrivals.remove(job)

    # -----------------------------------------------------
    def has_jobs(self):
        """Return True if any queue still has jobs."""
        return any([self.ready, self.wait, self.cpu, self.io, self.waiting_arrivals])

    # -----------------------------------------------------
    def step(self):
        """Advance one tick of simulation logic."""
        self.clock += 1

        # check for any new arrivals
        self.check_arrivals()

        # Move jobs around randomly for demo (replace with FCFS/RR/etc.)
        if self.cpu:
            job = self.cpu.pop(0)
            job.current_burst += 1
            job.remaining_quantum -= 1 # decrement the quantum
            if job.current_burst >= job.bursts[0]:
                job.state = "wait"
                job.current_burst = 0
                job.remaining_quantum = job.quantum
                self.wait.append(job)
            # Quantum expired before CPU burst finished
            elif job.remaining_quantum <= 0:
                job.state = "ready"
                job.remaining_quantum = job.quantum
                self.ready.append(job)
            else:
                self.cpu.append(job)
        elif self.ready:
            job = self.ready.pop(0)
            job.state = "running"
            self.cpu.append(job)

        # Random I/O completion
        if self.wait and random.random() < 0.1:
            job = self.wait.pop(0)
            job.state = "ready"
            self.ready.append(job)

    # -----------------------------------------------------
    def snapshot(self):
        """Return current state snapshot for visualization."""
        return {
            "clock": self.clock,
            "ready": [job.id for job in self.ready],
            "wait": [job.id for job in self.wait],
            "cpu": [job.id for job in self.cpu],
            "io": [job.id for job in self.io],
        }
