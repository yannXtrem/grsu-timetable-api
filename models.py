from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import time
from bson import ObjectId

@dataclass
class Lecturer:
    name: str

    def to_dict(self):
        return {'name': self.name}

    @classmethod
    def from_dict(cls, data):
        return cls(name=data['name'])

@dataclass
class Subject:
    name: str
    lecturer: Lecturer

    def to_dict(self):
        return {
            'name': self.name,
            'lecturer': self.lecturer.to_dict()
        }

    @classmethod
    def from_dict(cls, data):
        lecturer = Lecturer.from_dict(data['lecturer'])
        return cls(name=data['name'], lecturer=lecturer)

@dataclass
class ScheduleTime:
    start: time
    end: time

    def to_dict(self):
        return {
            'start': self.start.isoformat(timespec='minutes'),
            'end': self.end.isoformat(timespec='minutes')
        }

    @classmethod
    def from_dict(cls, data):
        start = time.fromisoformat(data['start'])
        end = time.fromisoformat(data['end'])
        return cls(start=start, end=end)

@dataclass
class ScheduleClass:
    subject: Subject
    time: ScheduleTime
    subgroup: str
    door: Optional[str] = None

    def to_dict(self):
        return {
            'subject': self.subject.to_dict(),
            'time': self.time.to_dict(),
            'subgroup': self.subgroup,
            'door': self.door
        }

    @classmethod
    def from_dict(cls, data):
        subject = Subject.from_dict(data['subject'])
        time = ScheduleTime.from_dict(data['time'])
        return cls(
            subject=subject,
            time=time,
            subgroup=data['subgroup'],
            door=data.get('door')
        )

@dataclass
class ScheduleDay:
    weekday: int          # 0 = Lundi
    monthday: int
    classes: List[ScheduleClass] = field(default_factory=list)

    def to_dict(self):
        return {
            'weekday': self.weekday,
            'monthday': self.monthday,
            'classes': [c.to_dict() for c in self.classes]
        }

    @classmethod
    def from_dict(cls, data):
        classes = [ScheduleClass.from_dict(c) for c in data['classes']]
        return cls(
            weekday=data['weekday'],
            monthday=data['monthday'],
            classes=classes
        )

@dataclass
class ScheduleWeek:
    week_number: int
    group_name: str
    days: List[ScheduleDay] = field(default_factory=list)
    _id: Optional[ObjectId] = None

    def to_dict(self, include_id=False):
        d = {
            'week_number': self.week_number,
            'group_name': self.group_name,
            'days': [day.to_dict() for day in self.days]
        }
        if include_id and self._id:
            d['_id'] = str(self._id)
        return d

    @classmethod
    def from_dict(cls, data):
        days = [ScheduleDay.from_dict(d) for d in data['days']]
        week = cls(
            week_number=data['week_number'],
            group_name=data['group_name'],
            days=days
        )
        if '_id' in data:
            week._id = data['_id'] if isinstance(data['_id'], ObjectId) else ObjectId(data['_id'])
        return week