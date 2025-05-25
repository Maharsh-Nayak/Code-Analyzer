from flask import Blueprint, request, jsonify
from utils.feedback_learner import FeedbackLearner

# Create blueprint
feedback = Blueprint('feedback', __name__)

# Initialize feedback learner
feedback_learner = FeedbackLearner()

@feedback.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    
    # Validate required fields
    required_fields = ['type', 'rating', 'feedback_text']
    if not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Missing required fields. Please provide type, rating, and feedback_text'
        }), 400
    
    feedback_type = data['type']
    if feedback_type not in ['code_analysis', 'repo_analysis', 'diagram']:
        return jsonify({
            'error': 'Invalid feedback type. Must be one of: code_analysis, repo_analysis, diagram'
        }), 400
    
    # Validate rating (1-5)
    try:
        rating = int(data['rating'])
        if not 1 <= rating <= 5:
            raise ValueError
    except ValueError:
        return jsonify({
            'error': 'Rating must be a number between 1 and 5'
        }), 400
    
    # Save feedback using the feedback learner
    feedback_learner.save_feedback(
        feedback_type=feedback_type,
        rating=rating,
        feedback_text=data['feedback_text'],
        additional_data=data.get('additional_data', {})
    )
    
    return jsonify({
        'message': 'Feedback submitted successfully',
        'status': 'success'
    })

@feedback.route('/api/get-feedback-stats', methods=['GET'])
def get_feedback_stats():
    # Get feedback statistics from the feedback learner
    stats = {}
    for feedback_type in ['code_analysis', 'repo_analysis', 'diagram']:
        improvements = feedback_learner.get_role_improvements(feedback_type)
        if improvements:
            stats[feedback_type] = {
                'total_feedback': improvements.get('total_feedback', 0),
                'average_rating': improvements.get('average_rating', 0),
                'recent_feedback': improvements.get('recent_feedback', [])
            }
        else:
            stats[feedback_type] = {
                'total_feedback': 0,
                'average_rating': 0,
                'recent_feedback': []
            }
    
    return jsonify(stats)

@feedback.route('/api/clear-feedback', methods=['POST'])
def clear_feedback():
    # This endpoint should be protected in production
    feedback_learner = FeedbackLearner()
    feedback_learner.feedback_data = {
        'code_analysis': [],
        'repo_analysis': [],
        'diagram': []
    }
    feedback_learner.save_feedback('code_analysis', 0, '', {})
    return jsonify({
        'message': 'All feedback data cleared',
        'status': 'success'
    }) 