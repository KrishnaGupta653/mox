"""
Playback Scheduler - Alarms, sleep timers, and scheduled playback
"""

import os
import json
import time
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger('mox.scheduler')


class PlaybackScheduler:
    def __init__(self):
        self.data_dir = Path.home() / '.local' / 'share' / 'mox' / 'schedules'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.schedules = {}
        self.active_jobs = {}
        self._lock = threading.Lock()
        
        # Load existing schedules
        self._load_schedules()
    
    def add_schedule(self, schedule_type: str, time_str: str, 
                     playlist: str, days: Optional[List[str]] = None) -> Dict:
        """Add a new schedule"""
        schedule_id = f"{schedule_type}_{int(time.time())}"
        
        try:
            # Parse time
            if schedule_type == 'sleep':
                # Sleep timer: time_str is minutes from now
                execute_at = datetime.now() + timedelta(minutes=int(time_str))
            else:
                # Alarm/reminder: time_str is HH:MM format
                today = datetime.now()
                hour, minute = map(int, time_str.split(':'))
                execute_at = today.replace(hour=hour, minute=minute, second=0)
                
                # If time has passed today, schedule for tomorrow
                if execute_at < today:
                    execute_at += timedelta(days=1)
            
            schedule = {
                'id': schedule_id,
                'type': schedule_type,
                'time': time_str,
                'playlist': playlist,
                'days': days or ['*'],  # '*' means daily
                'execute_at': execute_at.isoformat(),
                'active': True,
                'created_at': datetime.now().isoformat()
            }
            
            with self._lock:
                self.schedules[schedule_id] = schedule
                self._save_schedule(schedule_id, schedule)
                
                # Schedule the job
                self._schedule_job(schedule)
            
            return {
                'status': 'scheduled',
                'id': schedule_id,
                'execute_at': execute_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to add schedule: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def delete_schedule(self, schedule_id: str) -> Dict:
        """Delete a schedule"""
        with self._lock:
            if schedule_id in self.schedules:
                del self.schedules[schedule_id]
                
                # Remove job if active
                if schedule_id in self.active_jobs:
                    # In production, would cancel APScheduler job
                    del self.active_jobs[schedule_id]
                
                # Remove from disk
                schedule_file = self.data_dir / f"{schedule_id}.json"
                if schedule_file.exists():
                    schedule_file.unlink()
                
                return {'status': 'deleted', 'id': schedule_id}
            
            return {'status': 'error', 'message': 'Schedule not found'}
    
    def get_schedules(self) -> List[Dict]:
        """Get all active schedules"""
        with self._lock:
            return [
                {
                    'id': s['id'],
                    'type': s['type'],
                    'time': s['time'],
                    'playlist': s['playlist'],
                    'days': s['days'],
                    'next_run': s['execute_at'],
                    'active': s['active']
                }
                for s in self.schedules.values()
                if s.get('active', True)
            ]
    
    def snooze_alarm(self, schedule_id: str, minutes: int = 5) -> Dict:
        """Snooze an alarm"""
        with self._lock:
            if schedule_id not in self.schedules:
                return {'status': 'error', 'message': 'Schedule not found'}
            
            schedule = self.schedules[schedule_id]
            new_execute = datetime.now() + timedelta(minutes=minutes)
            
            schedule['execute_at'] = new_execute.isoformat()
            self._save_schedule(schedule_id, schedule)
            self._schedule_job(schedule)
            
            return {
                'status': 'snoozed',
                'execute_at': new_execute.isoformat()
            }
    
    def _schedule_job(self, schedule: Dict):
        """Schedule a job (placeholder - would use APScheduler in production)"""
        schedule_id = schedule['id']
        
        # In production, would use APScheduler:
        # self.scheduler.add_job(self._execute_schedule, 'date', 
        #                        run_date=datetime.fromisoformat(schedule['execute_at']),
        #                        args=[schedule])
        
        # For now, just mark as scheduled
        self.active_jobs[schedule_id] = {
            'scheduled': True,
            'execute_at': schedule['execute_at']
        }
        
        logger.info(f"Scheduled {schedule_id} for {schedule['execute_at']}")
    
    def _execute_schedule(self, schedule: Dict):
        """Execute a scheduled playback"""
        try:
            schedule_type = schedule['type']
            playlist = schedule['playlist']
            
            logger.info(f"Executing scheduled {schedule_type}: {playlist}")
            
            # In production, would call player API
            # For sleep timer, would fade out
            # For alarm, would fade in
            
            # Handle recurring schedules
            if schedule['days'] != ['*']:
                # Reschedule for next occurrence
                next_run = self._calculate_next_run(schedule)
                schedule['execute_at'] = next_run.isoformat()
                self._save_schedule(schedule['id'], schedule)
                self._schedule_job(schedule)
            else:
                # One-time schedule
                with self._lock:
                    schedule['active'] = False
                    self._save_schedule(schedule['id'], schedule)
            
        except Exception as e:
            logger.error(f"Failed to execute schedule: {e}")
    
    def _calculate_next_run(self, schedule: Dict) -> datetime:
        """Calculate next run time for recurring schedule"""
        days = schedule['days']
        hour, minute = map(int, schedule['time'].split(':'))
        
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0)
        
        # Find next matching day
        for i in range(1, 8):
            candidate = now + timedelta(days=i)
            day_name = candidate.strftime('%a').upper()
            
            if '*' in days or day_name in [d.upper() for d in days]:
                next_run = candidate
                break
        
        return next_run
    
    def _load_schedules(self):
        """Load schedules from disk"""
        for schedule_file in self.data_dir.glob("*.json"):
            try:
                with open(schedule_file, 'r') as f:
                    data = json.load(f)
                    schedule_id = data['id']
                    
                    # Only load active schedules
                    if data.get('active', True):
                        self.schedules[schedule_id] = data
                        self._schedule_job(data)
                        
            except Exception as e:
                logger.error(f"Failed to load schedule: {e}")
    
    def _save_schedule(self, schedule_id: str, data: Dict):
        """Save schedule to disk"""
        schedule_file = self.data_dir / f"{schedule_id}.json"
        
        try:
            with open(schedule_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedule: {e}")
    
    def get_sleep_timer_presets(self) -> List[Dict]:
        """Get common sleep timer presets"""
        return [
            {'label': '15 minutes', 'minutes': 15},
            {'label': '30 minutes', 'minutes': 30},
            {'label': '45 minutes', 'minutes': 45},
            {'label': '1 hour', 'minutes': 60},
            {'label': '2 hours', 'minutes': 120},
            {'label': 'Until end of track', 'minutes': -1}
        ]
    
    def get_alarm_presets(self) -> List[Dict]:
        """Get common alarm presets"""
        return [
            {'label': 'Wake up', 'time': '07:00', 'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']},
            {'label': 'Weekend chill', 'time': '09:00', 'days': ['Sat', 'Sun']},
            {'label': 'Lunch break', 'time': '12:00', 'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']},
            {'label': 'Evening wind-down', 'time': '22:00', 'days': ['*']}
        ]
