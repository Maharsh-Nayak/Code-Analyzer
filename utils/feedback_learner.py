import json
import os
from datetime import datetime
from collections import defaultdict

class FeedbackLearner:
    def __init__(self, feedback_file='feedback_data.json'):
        self.feedback_file = feedback_file
        self.feedback_data = self._load_feedback()
        self.role_improvements = self._analyze_feedback()

    def _load_feedback(self):
        if os.path.exists(self.feedback_file):
            with open(self.feedback_file, 'r') as f:
                return json.load(f)
        return {
            'code_analysis': [],
            'repo_analysis': [],
            'diagram': []
        }

    def _analyze_feedback(self):
        improvements = defaultdict(dict)
        
        # Analyze feedback for each role
        for feedback_type, entries in self.feedback_data.items():
            if feedback_type == 'code_analysis':
                role_feedback = defaultdict(list)
                
                # Group feedback by role
                for entry in entries:
                    role = entry.get('additional_data', {}).get('role')
                    if role:
                        role_feedback[role].append({
                            'rating': entry['rating'],
                            'feedback': entry['feedback_text'],
                            'timestamp': entry['timestamp']
                        })
                
                # Analyze each role's feedback
                for role, feedbacks in role_feedback.items():
                    if feedbacks:
                        # Calculate average rating
                        avg_rating = sum(f['rating'] for f in feedbacks) / len(feedbacks)
                        
                        # Get recent feedback (last 5)
                        recent_feedback = sorted(feedbacks, 
                                              key=lambda x: x['timestamp'], 
                                              reverse=True)[:5]
                        
                        # Extract common themes from negative feedback
                        negative_themes = []
                        for f in feedbacks:
                            if f['rating'] <= 3:
                                negative_themes.append(f['feedback'])
                        
                        improvements[role] = {
                            'average_rating': avg_rating,
                            'recent_feedback': recent_feedback,
                            'negative_themes': negative_themes,
                            'total_feedback': len(feedbacks)
                        }
        
        return improvements

    def get_role_improvements(self, role):
        return self.role_improvements.get(role, {})

    def update_instructions(self, base_instructions, role):
        improvements = self.get_role_improvements(role)
        if not improvements:
            return base_instructions

        # Get recent feedback themes
        recent_themes = [f['feedback'] for f in improvements.get('recent_feedback', [])]
        negative_themes = improvements.get('negative_themes', [])
        
        # Create improvement instructions
        improvement_instructions = []
        
        if negative_themes:
            improvement_instructions.append(
                "Based on previous feedback, please avoid these issues:\n" +
                "\n".join(f"- {theme}" for theme in negative_themes[:3])
            )
        
        if recent_themes:
            improvement_instructions.append(
                "Recent feedback suggests focusing on:\n" +
                "\n".join(f"- {theme}" for theme in recent_themes[:3])
            )
        
        # Combine with base instructions
        if improvement_instructions:
            return base_instructions + "\n\n" + "\n\n".join(improvement_instructions)
        
        return base_instructions

    def save_feedback(self, feedback_type, rating, feedback_text, additional_data):
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'rating': rating,
            'feedback_text': feedback_text,
            'additional_data': additional_data
        }
        
        self.feedback_data[feedback_type].append(feedback_entry)
        
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback_data, f, indent=4)
        
        # Update improvements after saving new feedback
        self.role_improvements = self._analyze_feedback() 