# =========================================================
# scheduler.py  – Pure simulation logic (no pygame)
# =========================================================
import random

class Job:
    def __init__(self, job_id, arrival_time, bursts):
        self.id = job_id
        self.arrival_time = arrival_time
        self.bursts = bursts  # list of (type, duration) tuples
        self.current_burst = 0
        self.time_in_burst = 0
        self.state = "NEW"  # states - begin in the "new" queue
        
    def get_current_burst(self):
        if self.current_burst < len(self.bursts):
            return self.bursts[self.current_burst]
        return None
    
    def advance_burst(self):
        self.time_in_burst += 1
        burst = self.get_current_burst()
        if burst and self.time_in_burst >= burst[1]:
            self.current_burst += 1
            self.time_in_burst = 0
            return True  # Burst completed
        return False
    
    def is_complete(self):
        return self.current_burst >= len(self.bursts)


class Scheduler:
    def __init__(self, jobs, cpu_max=1, io_max=2, quantum=3):
        self.jobs = sorted(jobs, key=lambda j: j.arrival_time)
        self.clock = 0
        self.quantum = quantum
        self.cpu_max = cpu_max
        self.io_max = io_max
        
        # Queues
        self.ready = []
        self.wait = []
        self.cpu = []
        self.io = []
        self.terminated = []
        
        # Track quantum usage for RR
        self.cpu_quantum_remaining = {}

    # singular step for process(es)
    def step(self):
        # check for new arrivals
        self._check_arrivals()
        # process CPU
        self._process_cpu()
        # process I/O
        self._process_io()
        # load jobs into CPU/IO if space available
        self._load_cpu()
        self._load_io()
        # add a clock tick
        self.clock += 1

    # checks if there are any new arrived processes
    def _check_arrivals(self):
        for job in self.jobs[:]:
            if job.arrival_time == self.clock and job.state == "NEW":
                job.state = "READY"
                self.ready.append(job)
                self.jobs.remove(job)

    # allows the process to access the CPU
    def _process_cpu(self):
        for job in self.cpu[:]:
            burst_done = job.advance_burst()
            # check the quantum for Round Robin scheduling
            if job in self.cpu_quantum_remaining:
                self.cpu_quantum_remaining[job] -= 1
                if self.cpu_quantum_remaining[job] <= 0 and not burst_done:
                    # quantum expired but burst not done - so preempt
                    job.state = "READY"
                    self.cpu.remove(job)
                    self.ready.append(job)
                    del self.cpu_quantum_remaining[job]    # delete the quantum for the job
                    continue
            # when the burst is finished
            if burst_done:
                self.cpu.remove(job)
                if job in self.cpu_quantum_remaining:
                    del self.cpu_quantum_remaining[job]
                # when the job is finished, send to the terminated queue
                if job.is_complete():
                    job.state = "TERMINATED"
                    self.terminated.append(job)
                else:
                    # the next burst must be I/O
                    job.state = "WAITING"
                    self.wait.append(job)

    # allows the process to achieve IO access
    def _process_io(self):
        """Advance I/O jobs and handle burst completion"""
        for job in self.io[:]:
            burst_done = job.advance_burst()
            
            if burst_done:
                self.io.remove(job)
                
                if job.is_complete():
                    job.state = "TERMINATED"
                    self.terminated.append(job)
                else:
                    # Next burst must be CPU
                    job.state = "READY"
                    self.ready.append(job)

    # moves the processes from ready to CPU
    def _load_cpu(self):
        while len(self.cpu) < self.cpu_max and self.ready:
            job = self.ready.pop(0)  # FCFS/RR order
            job.state = "RUNNING"
            self.cpu.append(job)
            self.cpu_quantum_remaining[job] = self.quantum
    
    # moves the processes from wiait to IO
    def _load_io(self):
        while len(self.io) < self.io_max and self.wait:
            job = self.wait.pop(0)
            job.state = "WAITING"
            self.io.append(job)

    # simply checks if the simulation is finished
    def has_jobs(self):
        return (len(self.jobs) > 0 or 
                len(self.ready) > 0 or 
                len(self.wait) > 0 or 
                len(self.cpu) > 0 or 
                len(self.io) > 0)
    
    def snapshot(self):
        return {
            "clock": self.clock,
            "ready": [job.id for job in self.ready],
            "wait": [job.id for job in self.wait],
            "cpu": [job.id for job in self.cpu],
            "io": [job.id for job in self.io],
            "terminated": [job.id for job in self.terminated],
            "cpu_max": self.cpu_max,
            "io_max": self.io_max,
            "quantum": self.quantum
        }


# Example usage for testing
if __name__ == "__main__":
    # Create sample jobs
    jobs = [
        Job("P1", 0, [("CPU", 5), ("IO", 3), ("CPU", 4)]),
        Job("P2", 1, [("CPU", 3), ("IO", 2), ("CPU", 2)]),
        Job("P3", 2, [("CPU", 6), ("IO", 4), ("CPU", 3)]),
    ]
    
    scheduler = Scheduler(jobs, cpu_max=1, io_max=2, quantum=3)
    
    # run the simulation
    while scheduler.has_jobs():
        print(f"Clock {scheduler.clock}: {scheduler.snapshot()}")
        scheduler.step()
    
    print(f"Simulation complete at clock {scheduler.clock}")
