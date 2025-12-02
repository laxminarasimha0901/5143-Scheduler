# schedulers/rr.py
from pkg import Scheduler
from collections import deque

class RRScheduler(Scheduler):
    def __init__(self, num_cpus=1, num_ios=1, quantum=4, verbose=False):
        super().__init__(num_cpus, num_ios, verbose)  # ✅ Must call this FIRST
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.quantum = quantum
        self.verbose = verbose
        
        # Queues
        #self.ready_queue = deque()      # Ready processes
        #self.wait_queue = deque()      # Processes waiting for I/O
        self.cpu_queue = [None] * num_cpus  # Currently running processes on each CPU
        self.io_queue = [None] * num_ios   # Currently running processes on each I/O device
        #self.finished = []              # Completed processes
        
        #self.clock = 0
        self.total_context_switches = 0
    
    def add_process(self, process):
        """Add a process to the ready queue"""
        if process.arrival_time == 0:
            process.state = "ready"
        else:
            process.state = "new"
        process.remaining_quantum = process.quantum
        self.ready_queue.append(process)
    
    def step(self):
        """Execute one time step of the simulation"""
        if self.clock.time % 1 == 0:  # Print every tick
            print(f"Time: {self.clock.time}")
            print(f"  Ready queue: {[p.pid for p in self.ready_queue]}")
            print(f"  Wait queue: {[p.pid for p in self.wait_queue]}")
            print(f"  CPUs: {[cpu.current.pid if cpu.current else None for cpu in self.cpus]}")
            print(f"  IOs: {[io.current.pid if io.current else None for io in self.io_devices]}")
            print(f"  Finished: {len(self.finished)}")
    
        if self.clock.time > 10000:  # Safety limit
            print("ERROR: Simulation exceeded 10000 time units - likely stuck in infinite loop")
            print(f"Ready: {len(self.ready_queue)}, Wait: {len(self.wait_queue)}")
            print(f"CPUs busy: {[cpu.is_busy() for cpu in self.cpus]}")
            print(f"IOs busy: {[io.is_busy() for io in self.io_devices]}")
            raise RuntimeError("Infinite loop detected")

        self.clock.tick()
        
        # Handle process arrivals
        self._handle_arrivals()
        
        # Process currently running jobs on CPUs
        self._process_cpus()
        
        # Process currently running jobs on I/O devices
        self._process_io_devices()
        
        # Dispatch ready processes to available CPUs
        self._dispatch_to_cpus()
        
        # Dispatch waiting processes to available I/O devices
        self._dispatch_to_io_devices()

    def has_jobs(self):
        return (len(self.ready_queue) > 0 or 
                len(self.wait_queue) > 0 or 
                any(p is not None for p in self.cpu_queue) or 
                any(p is not None for p in self.io_queue))
    
    def _handle_arrivals(self):
        """Move processes from new state to ready queue when they arrive"""
        arrived_processes = []
        for process in list(self.ready_queue):  # Use list() to avoid modifying during iteration
            if process.state == "new" and process.arrival_time <= self.clock.time:
                process.state = "ready"
        
        # Move arrived processes to the end of the ready queue
        for process in arrived_processes:
            self.ready_queue.append(self.ready_queue.popleft())
    
    def _process_cpus(self):
        """Process currently running jobs on all CPUs"""
        for cpu in self.cpus:
            if cpu.is_busy():
                current_process = cpu.current
            
                # Decrement remaining quantum
                current_process.remaining_quantum -= 1
            
                # Let the CPU tick (this advances the burst)
                finished_process = cpu.tick()
            
                if finished_process:
                    # CPU burst completed
                    if finished_process.is_complete():
                        # Process is completely done
                        finished_process.state = "finished"
                        finished_process.end_time = self.clock.time
                        finished_process.turnaround_time = self.clock.time - finished_process.arrival_time
                        self.finished.append(finished_process)
                    else:
                        # Next burst is I/O
                        finished_process.state = "waiting"
                        self.wait_queue.append(finished_process)
                elif current_process.remaining_quantum <= 0:
                    # Quantum expired but burst not complete - preempt
                    cpu.current = None
                    current_process.state = "ready"
                    current_process.remaining_quantum = self.quantum
                    self.ready_queue.append(current_process)
                    self.total_context_switches += 1
    
    def _process_io_devices(self):
        """Process currently running jobs on all I/O devices"""
        for io_dev in self.io_devices:
            if io_dev.is_busy():
                current_process = io_dev.current
            
                # Debug: Check what burst we're processing
                if self.clock.time % 100 == 0:
                    burst = current_process.current_burst()
                    print(f"  DEBUG IO: Process {current_process.pid} burst: {burst}")
            
                # Let the I/O device tick (this advances the burst)
                finished_process = io_dev.tick()
            
                if finished_process:
                    # I/O burst completed
                    if finished_process.is_complete():
                        # Process is completely done
                        finished_process.state = "finished"
                        finished_process.end_time = self.clock.time
                        finished_process.turnaround_time = self.clock.time - finished_process.arrival_time
                        self.finished.append(finished_process)
                    else:
                        # Next burst is CPU, move back to ready queue
                        finished_process.state = "ready"
                        finished_process.remaining_quantum = self.quantum
                        self.ready_queue.append(finished_process)

    def _dispatch_to_cpus(self):
        """Dispatch ready processes to available CPUs"""
        for cpu in self.cpus:
            if not cpu.is_busy() and len(self.ready_queue) > 0:
                process = self.ready_queue.popleft()
                process.remaining_quantum = self.quantum
                cpu.assign(process)
                self.total_context_switches += 1
    
    def _dispatch_to_io_devices(self):
        """Dispatch waiting processes to available I/O devices"""
        for io_dev in self.io_devices:
            # Check if device is idle and there are waiting processes
            if io_dev.current is None and len(self.wait_queue) > 0:
                process = self.wait_queue.popleft()
                process.state = "waiting"
                io_dev.current = process  # Assign directly