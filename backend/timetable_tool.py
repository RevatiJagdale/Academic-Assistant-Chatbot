# backend/timetable_tool.py
import pandas as pd
import os, re
from datetime import datetime

DATA_PATH = "data/timetable.csv"

class TimetableTool:
    def __init__(self, file_path=DATA_PATH):
        # Note: No LLM instance needed here anymore
        if not os.path.exists(file_path):
            print(f"[ERROR] Timetable CSV not found at {file_path}")
            self.df = pd.DataFrame(columns=["day", "time", "username", "course", "venue"])
        else:
            self.df = pd.read_csv(file_path, dtype=str).fillna("")
            self.df.columns = self.df.columns.str.strip().str.lower()
        
        self.all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        self.all_slots = sorted(list(self.df['time'].unique())) if not self.df.empty else []
        
    def _get_day_from_query(self, query: str) -> str:
        query_lower = query.lower()
        today_index = datetime.now().weekday()
        
        if "tomorrow" in query_lower:
            day_index = (today_index + 1) % 7
            return self.all_days[day_index] if day_index < 6 else "Sunday"
        
        for day in self.all_days:
            if day.lower() in query_lower:
                return day
        
        # Default to today
        return self.all_days[today_index] if today_index < 6 else "Sunday"

    def _get_time_from_query(self, query: str) -> str | None:
        """
        Robust time extraction. Matches '8', '08', '8am', '8:30', '1 pm'.
        """
        q_lower = query.lower()
        
        # Extract number part (e.g., "8", "10", "08")
        match = re.search(r'(\bat\s*|\s|^)(\d{1,2})(:(\d{2}))?(\s*(am|pm))?', q_lower)
        
        if not match:
            return None

        hour = int(match.group(2))
        minute = match.group(4) or "" 
        meridiem = match.group(6) 

        # Handle PM conversion
        if meridiem == "pm" and hour < 12: hour += 12
        if meridiem == "am" and hour == 12: hour = 0

        # Generate search prefixes
        prefix_variants = [f"{hour}:", f"{hour:02d}:"]
        if minute:
            prefix_variants = [f"{hour}:{minute}", f"{hour:02d}:{minute}"]

        # Scan CSV slots
        for slot in self.all_slots:
            for prefix in prefix_variants:
                if slot.startswith(prefix):
                    return slot
        return None

    def _find_free_faculty(self, day: str, time_slot: str) -> str:
        if self.df.empty: return "Timetable data is missing."
        try:
            busy_faculty = self.df[
                (self.df['day'].str.lower() == day.lower()) &
                (self.df['time'] == time_slot)
            ]['username'].str.lower().unique()
            
            all_faculty = self.df['username'].str.lower().unique()
            free_faculty_set = set(all_faculty) - set(busy_faculty)
            
            if not free_faculty_set:
                return f"No faculty are free on {day} at {time_slot}."
            
            free_list = sorted(list(free_faculty_set))[:30]
            return f"Faculty free on {day} at {time_slot}:\n{', '.join(free_list)}"
        except Exception as e:
            return f"Error calculating free faculty: {e}"

    def _find_free_classrooms(self, day: str, time_slot: str) -> str:
        if self.df.empty: return "Timetable data is missing."
        try:
            busy_venues = self.df[
                (self.df['day'].str.lower() == day.lower()) &
                (self.df['time'] == time_slot)
            ]['venue'].str.lower().unique()
            
            all_venues = self.df['venue'].str.lower().unique()
            free_venues_set = set(all_venues) - set(busy_venues)
            
            if not free_venues_set:
                return f"No classrooms are free on {day} at {time_slot}."
            
            return f"Classrooms free on {day} at {time_slot}:\n{', '.join(sorted(list(free_venues_set)))}"
        except Exception as e:
            return f"Error calculating free classrooms: {e}"

    def _get_faculty_schedule(self, faculty_name: str) -> str:
        if self.df.empty: return "Timetable data is missing."
        schedule = self.df[self.df['username'].str.contains(faculty_name, case=False, na=False)]
        if schedule.empty:
            return f"No schedule found for '{faculty_name}'."
        
        response = f"Schedule for {faculty_name}:\n"
        for _, row in schedule.sort_values(by=['day', 'time']).iterrows():
            response += f"- {row['day']} {row['time']}: {row['course']} ({row['venue']})\n"
        return response

    def _get_subject_teachers(self, subject_name: str) -> str:
        if self.df.empty: return "Timetable data is missing."
        result = self.df[self.df['course'].str.contains(subject_name, case=False, na=False)]
        if result.empty:
            return f"No teachers found for subject '{subject_name}'."
        teachers = result['username'].unique()
        return f"Subject '{subject_name}' is taught by: {', '.join(teachers)}"

    def query_timetable(self, question: str) -> str:
        q_lower = question.lower()
        
        # LOGIC ROUTER
        if "free" in q_lower:
            day = self._get_day_from_query(q_lower)
            time_slot = self._get_time_from_query(q_lower)
            
            if not time_slot:
                # Return a helpful message so the LLM can explain WHY it failed
                return f"Could not find a valid time slot in the question. Available times in data start with: {', '.join(self.all_slots[:3])}..."
            
            if day == "Sunday": return "It's Sunday, everyone is free!"
            
            if any(x in q_lower for x in ["classroom", "venue", "room", "lab"]):
                return self._find_free_classrooms(day, time_slot)
            return self._find_free_faculty(day, time_slot)
        
        if "schedule" in q_lower and "for" in q_lower:
            name = q_lower.split("for ")[-1].strip("? .")
            return self._get_faculty_schedule(name)
            
        if "who teaches" in q_lower or "taught by" in q_lower:
             if "who teaches" in q_lower: subj = q_lower.split("teaches ")[-1].strip("? .")
             else: subj = q_lower.split("taught by ")[-1].strip("? .")
             return self._get_subject_teachers(subj)

        return "I can help with: who is free at [time], schedule for [faculty], or who teaches [subject]."