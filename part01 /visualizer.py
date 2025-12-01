# visualizer.py
from collections import defaultdict
import csv

class GanttVisualizer:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.execution_intervals = []
        self.running_jobs = {}  # Tracks start time of currently running jobs
    
    def capture_execution_intervals(self):
        """Capture execution intervals by monitoring state changes during simulation"""
        prev_snapshot = None
        
        while self.scheduler.has_jobs():
            current_snapshot = self.scheduler.snapshot()
            
            if prev_snapshot is not None:
                # Detect jobs that started and stopped running
                prev_cpu_jobs = set(prev_snapshot['cpu'])
                current_cpu_jobs = set(current_snapshot['cpu'])
                
                # Jobs that newly started running
                newly_running = current_cpu_jobs - prev_cpu_jobs
                for job_id in newly_running:
                    self.running_jobs[job_id] = current_snapshot['clock']
                
                # Jobs that stopped running
                stopped_running = prev_cpu_jobs - current_cpu_jobs
                for job_id in stopped_running:
                    if job_id in self.running_jobs:
                        start_time = self.running_jobs[job_id]
                        end_time = current_snapshot['clock']
                        self.execution_intervals.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'job_id': job_id,
                            'resource_type': 'CPU',
                            'duration': end_time - start_time
                        })
                        del self.running_jobs[job_id]
            
            prev_snapshot = current_snapshot
            self.scheduler.step()
        
        # Handle any remaining running jobs at simulation end
        if prev_snapshot and self.running_jobs:
            end_time = prev_snapshot['clock']
            for job_id in self.running_jobs:
                start_time = self.running_jobs[job_id]
                self.execution_intervals.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'job_id': job_id,
                    'resource_type': 'CPU',
                    'duration': end_time - start_time
                })
    
    def display_detailed_gantt_chart(self):
        """Display a detailed text-based Gantt chart"""
        if not self.execution_intervals:
            print("No execution intervals to display.")
            return
        
        print("\n" + "=" * 90)
        print("DETAILED GANTT CHART")
        print("=" * 90)
        
        # Display execution intervals in chronological order
        print(f"{'Job':<6} {'Start':<6} {'End':<6} {'Duration':<6} {'Resource':<6}")
        print("-" * 50)
        
        for interval in sorted(self.execution_intervals, key=lambda x: x['start_time']):
            print(f"{interval['job_id']:<6} {interval['start_time']:<6} "
                  f"{interval['end_time']:<6} {interval['duration']:<6} {interval['resource_type']:<6}")
        
        # Display timeline summary
        max_time = max(interval['end_time'] for interval in self.execution_intervals)
        total_cpu_time = sum(interval['duration'] for interval in self.execution_intervals)
        
        print("\n" + "-" * 50)
        print("GANTT CHART SUMMARY")
        print("-" * 50)
        print(f"Total simulation time:     {max_time} time units")
        print(f"Total CPU execution time: {total_cpu_time} time units")
        print(f"CPU utilization:          {total_cpu_time/max_time*100:.1f}%")
        print(f"Number of CPU bursts:    {len(self.execution_intervals)}")
    
    def export_timeline_to_csv(self, filename):
        """Export the execution timeline to a CSV file"""
        if not self.execution_intervals:
            print("No execution intervals to export.")
            return
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['start_time', 'end_time', 'job_id', 'resource_type', 'duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for interval in sorted(self.execution_intervals, key=lambda x: x['start_time']):
                writer.writerow(interval)
        
        print(f"Timeline successfully exported to {filename}")
    
    def get_gantt_data(self):
        """Return the collected execution intervals for further processing"""
        return self.execution_intervals

def run_simulation_with_gantt(scheduler, output_filename=None):
    """Run the simulation and generate Gantt chart visualization"""
    visualizer = GanttVisualizer(scheduler)
    
    # Capture all execution intervals during simulation
    visualizer.capture_execution_intervals()
    
    # Display the detailed Gantt chart
    visualizer.display_detailed_gantt_chart()
    
    # Export timeline to CSV if filename provided
    if output_filename:
        visualizer.export_timeline_to_csv(output_filename)
    
    return visualizer

# Example usage
if __name__ == "__main__":
    from scheduler import Scheduler, Job  # Import from your existing scheduler file
    
    # Create sample jobs
    jobs = [
        Job("P1", 0, [("CPU", 5), ("IO", 3), ("CPU", 4)]),
        Job("P2", 1, [("CPU", 3), ("IO", 2), ("CPU", 2)]),
        Job("P3", 2, [("CPU", 6), ("IO", 4), ("CPU", 3)]),
    ]
    
    scheduler = Scheduler(jobs, cpu_max=1, io_max=2, quantum=3)
    
    # Run simulation and generate Gantt chart
    visualizer = run_simulation_with_gantt(scheduler, "timeline.csv")
