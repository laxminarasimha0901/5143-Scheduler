# pygame_visualizer.py
import pygame
import sys
from collections import defaultdict

# Add all the pygame visualization code here...

# Color scheme
COLORS = {
    'background': (20, 20, 30),
    'panel': (40, 40, 50),
    'text': (220, 220, 220),
    'new': (100, 100, 100),
    'ready': (70, 130, 180),
    'running': (50, 205, 50),
    'waiting': (255, 165, 0),
    'io_waiting': (255, 140, 0),
    'finished': (147, 112, 219),
    'cpu': (70, 160, 70),
    'io': (255, 200, 50),
    'timeline_bg': (30, 30, 40),
    'grid': (60, 60, 70)
}

class PygameVisualizer:
    def __init__(self, scheduler, width=1400, height=900, fps=2):
        pygame.init()
        self.scheduler = scheduler
        self.width = width
        self.height = height
        self.fps = fps
        
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Process Scheduler Visualization")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        self.font_large = pygame.font.Font(None, 32)
        
        self.running = True
        self.paused = False
        self.step_mode = False
        
        # Timeline tracking
        self.timeline_history = []
        self.max_timeline_length = 100
        
    def draw_text(self, text, x, y, color=None, font=None):
        if color is None:
            color = COLORS['text']
        if font is None:
            font = self.font
        text_surface = font.render(str(text), True, color)
        self.screen.blit(text_surface, (x, y))
    
    def draw_panel(self, x, y, width, height, title):
        """Draw a panel with title"""
        pygame.draw.rect(self.screen, COLORS['panel'], (x, y, width, height))
        pygame.draw.rect(self.screen, COLORS['grid'], (x, y, width, height), 2)
        self.draw_text(title, x + 10, y + 5, font=self.font_small)
    
    def draw_process_box(self, process_id, x, y, width, height, state):
        """Draw a single process box"""
        color = COLORS.get(state.lower(), COLORS['panel'])
        pygame.draw.rect(self.screen, color, (x, y, width, height))
        pygame.draw.rect(self.screen, COLORS['text'], (x, y, width, height), 1)
        
        # Draw process ID
        text = str(process_id) if process_id is not None else "IDLE"
        text_surface = self.font_small.render(text, True, COLORS['text'])
        text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surface, text_rect)
    
    def draw_queue_area(self, x, y, width, height, title, process_list, state):
        """Draw a queue area with processes"""
        self.draw_panel(x, y, width, height, title)
        
        # Draw processes in queue
        box_width = 60
        box_height = 40
        margin = 10
        start_y = y + 30
        
        for i, pid in enumerate(process_list):
            row = i // 5
            col = i % 5
            px = x + margin + col * (box_width + margin)
            py = start_y + row * (box_height + margin)
            
            if py + box_height < y + height:
                self.draw_process_box(pid, px, py, box_width, box_height, state)
    
    def draw_cpu_io_resources(self, x, y, width, height):
        """Draw CPU and I/O resources"""
        self.draw_panel(x, y, width, height, "CPU & I/O Resources")
        
        # CPU resources
        cpu_y = y + 40
        cpu_label_y = y + 30
        self.draw_text("CPUs:", x + 10, cpu_label_y, font=self.font_small)
        
        box_width = 80
        box_height = 50
        margin = 10
        
        for i, process in enumerate(self.scheduler.cpu_queue):
            px = x + 80 + i * (box_width + margin)
            py = cpu_y
            
            if process is not None:
                self.draw_process_box(process.pid, px, py, box_width, box_height, 'running')
                # Show remaining burst time if available
                if hasattr(process, 'get_current_burst'):
                    burst = process.get_current_burst()
                    if burst and 'cpu' in burst:
                        remaining = burst['cpu'] - process.time_in_burst
                        self.draw_text(f"T:{remaining}", px + 5, py + box_height + 2, 
                                     color=COLORS['text'], font=self.font_small)
            else:
                self.draw_process_box(None, px, py, box_width, box_height, 'panel')
        
        # I/O resources
        io_y = y + 120
        io_label_y = y + 110
        self.draw_text("I/O Devices:", x + 10, io_label_y, font=self.font_small)
        
        for i, process in enumerate(self.scheduler.io_queue):
            px = x + 80 + i * (box_width + margin)
            py = io_y
            
            if process is not None:
                self.draw_process_box(process.pid, px, py, box_width, box_height, 'io_waiting')
                # Show remaining burst time if available
                if hasattr(process, 'get_current_burst'):
                    burst = process.get_current_burst()
                    if burst and 'io' in burst:
                        remaining = burst['io']['duration'] - process.time_in_burst
                        self.draw_text(f"T:{remaining}", px + 5, py + box_height + 2,
                                     color=COLORS['text'], font=self.font_small)
            else:
                self.draw_process_box(None, px, py, box_width, box_height, 'panel')
    
    def draw_timeline(self, x, y, width, height):
        """Draw execution timeline at the bottom"""
        self.draw_panel(x, y, width, height, "Execution Timeline (Recent History)")
        
        if not self.timeline_history:
            return
        
        timeline_y = y + 35
        bar_height = 20
        margin = 2
        
        # Get unique process IDs
        all_pids = set()
        for snapshot in self.timeline_history:
            for pid in snapshot['cpu']:
                if pid is not None:
                    all_pids.add(pid)
        
        sorted_pids = sorted(all_pids)
        
        # Calculate bar width based on timeline length
        bar_width = max(5, (width - 40) // len(self.timeline_history))
        
        # Draw timeline for each process
        for idx, pid in enumerate(sorted_pids):
            py = timeline_y + idx * (bar_height + margin)
            
            if py + bar_height < y + height - 10:
                self.draw_text(f"{pid}:", x + 10, py + 3, font=self.font_small)
                
                # Draw bars for when this process was running
                for i, snapshot in enumerate(self.timeline_history):
                    bx = x + 50 + i * bar_width
                    
                    if pid in snapshot['cpu']:
                        color = COLORS['running']
                    else:
                        color = COLORS['timeline_bg']
                    
                    pygame.draw.rect(self.screen, color, (bx, py, bar_width - 1, bar_height))
        
        # Draw time markers
        marker_y = y + height - 20
        step = max(1, len(self.timeline_history) // 10)
        for i in range(0, len(self.timeline_history), step):
            if i < len(self.timeline_history):
                clock_time = self.timeline_history[i]['clock']
                mx = x + 50 + i * bar_width
                self.draw_text(str(clock_time), mx, marker_y, font=self.font_small)
    
    def draw_stats(self, x, y, width, height):
        """Draw simulation statistics"""
        self.draw_panel(x, y, width, height, "Statistics")
        
        snapshot = self.scheduler.snapshot()
        
        stats_y = y + 30
        line_height = 25
        
        stats = [
            f"Clock: {snapshot['clock']}",
            f"Not Arrived: {len(snapshot.get('not_arrived', []))}",
            f"Ready Queue: {len(snapshot['ready'])}",
            f"Wait Queue: {len(snapshot['wait'])}",
            f"Running: {sum(1 for p in snapshot['cpu'] if p is not None)}",
            f"I/O Active: {sum(1 for p in snapshot['io'] if p is not None)}",
            f"Finished: {len(snapshot['finished'])}",
        ]
        
        for i, stat in enumerate(stats):
            self.draw_text(stat, x + 10, stats_y + i * line_height, font=self.font_small)
        
        # Add quantum info if available
        if 'quantum' in snapshot:
            self.draw_text(f"Quantum: {snapshot['quantum']}", 
                          x + 10, stats_y + len(stats) * line_height, font=self.font_small)
    
    def draw_legend(self, x, y):
        """Draw color legend"""
        legend_items = [
            ('New/Not Arrived', 'new'),
            ('Ready', 'ready'),
            ('Running (CPU)', 'running'),
            ('Waiting (I/O)', 'io_waiting'),
            ('Finished', 'finished'),
        ]
        
        box_size = 15
        spacing = 25
        
        for i, (label, color_key) in enumerate(legend_items):
            ly = y + i * spacing
            pygame.draw.rect(self.screen, COLORS[color_key], (x, ly, box_size, box_size))
            pygame.draw.rect(self.screen, COLORS['text'], (x, ly, box_size, box_size), 1)
            self.draw_text(label, x + box_size + 5, ly, font=self.font_small)
    
    def draw_controls(self, x, y):
        """Draw control instructions"""
        controls = [
            "SPACE: Pause/Resume",
            "S: Step Forward",
            "Q/ESC: Quit",
            f"Speed: {self.fps} FPS"
        ]
        
        for i, control in enumerate(controls):
            self.draw_text(control, x, y + i * 20, font=self.font_small)
    
    def draw_frame(self):
        """Draw a single frame"""
        self.screen.fill(COLORS['background'])
        
        # Get current snapshot
        snapshot = self.scheduler.snapshot()
        
        # Layout dimensions
        queue_width = 350
        queue_height = 150
        margin = 20
        
        # Draw queue areas
        self.draw_queue_area(margin, margin, queue_width, queue_height, 
                            "Not Arrived Queue", 
                            snapshot.get('not_arrived', []), 'new')
        
        self.draw_queue_area(margin, margin + queue_height + margin, 
                            queue_width, queue_height,
                            "Ready Queue", snapshot['ready'], 'ready')
        
        self.draw_queue_area(margin, margin + 2 * (queue_height + margin),
                            queue_width, queue_height,
                            "Wait Queue", snapshot['wait'], 'waiting')
        
        self.draw_queue_area(margin, margin + 3 * (queue_height + margin),
                            queue_width, queue_height,
                            "Finished Queue", snapshot['finished'], 'finished')
        
        # Draw CPU and I/O resources
        resource_x = queue_width + 2 * margin
        self.draw_cpu_io_resources(resource_x, margin, 600, 220)
        
        # Draw stats
        stats_width = 250
        stats_x = self.width - stats_width - margin
        self.draw_stats(stats_x, margin, stats_width, 300)
        
        # Draw legend
        self.draw_legend(stats_x, margin + 320)
        
        # Draw controls
        self.draw_controls(stats_x, margin + 500)
        
        # Draw timeline
        timeline_height = 200
        timeline_y = self.height - timeline_height - margin
        self.draw_timeline(margin, timeline_y, self.width - 2 * margin, timeline_height)
        
        # Draw title
        title = f"Process Scheduler Simulation - {self.scheduler.__class__.__name__}"
        if self.paused:
            title += " [PAUSED]"
        self.draw_text(title, self.width // 2 - 200, 5, font=self.font_large)
        
        pygame.display.flip()
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_s:
                    self.step_mode = True
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                elif event.key == pygame.K_UP:
                    self.fps = min(60, self.fps + 1)
                elif event.key == pygame.K_DOWN:
                    self.fps = max(1, self.fps - 1)
    
    def run_simulation(self):
        """Run the visualization simulation"""
        while self.running and self.scheduler.has_jobs():
            self.handle_events()
            
            if not self.paused or self.step_mode:
                # Store snapshot for timeline
                snapshot = self.scheduler.snapshot()
                self.timeline_history.append(snapshot)
                
                # Keep timeline history limited
                if len(self.timeline_history) > self.max_timeline_length:
                    self.timeline_history.pop(0)
                
                # Step the scheduler
                self.scheduler.step()
                self.step_mode = False
            
            self.draw_frame()
            self.clock.tick(self.fps)
        
        # Show final state
        if self.running:
            final_snapshot = self.scheduler.snapshot()
            self.timeline_history.append(final_snapshot)
            
            # Wait for user to close
            waiting = True
            while waiting and self.running:
                self.handle_events()
                self.draw_frame()
                
                # Draw completion message
                completion_text = "SIMULATION COMPLETE - Press Q to exit"
                text_surface = self.font_large.render(completion_text, True, COLORS['running'])
                text_rect = text_surface.get_rect(center=(self.width // 2, self.height // 2))
                
                # Draw semi-transparent background
                overlay = pygame.Surface((text_rect.width + 40, text_rect.height + 20))
                overlay.set_alpha(200)
                overlay.fill(COLORS['background'])
                self.screen.blit(overlay, (text_rect.x - 20, text_rect.y - 10))
                
                self.screen.blit(text_surface, text_rect)
                pygame.display.flip()
                self.clock.tick(10)
        
        pygame.quit()


def run_pygame_visualization(scheduler, fps=2):
    """
    Run pygame visualization of the scheduler
    
    Args:
        scheduler: The scheduler instance to visualize
        fps: Frames per second (simulation speed)
    """
    visualizer = PygameVisualizer(scheduler, fps=fps)
    visualizer.run_simulation()


# Example usage
if __name__ == "__main__":
    from pkg.scheduler import Scheduler, Job
    
    # Create sample jobs
    jobs = [
        Job("P1", 0, [("CPU", 5), ("IO", 3), ("CPU", 4)]),
        Job("P2", 1, [("CPU", 3), ("IO", 2), ("CPU", 2)]),
        Job("P3", 2, [("CPU", 6), ("IO", 4), ("CPU", 3)]),
    ]
    
    scheduler = Scheduler(jobs, cpu_max=2, io_max=2, quantum=3)
    run_pygame_visualization(scheduler, fps=2)