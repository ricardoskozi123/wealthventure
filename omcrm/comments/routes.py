from omcrm.activities.models import Activity

@comments.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    """AJAX endpoint for adding comments to various entities"""
    comment_text = request.form.get('comment_text', '').strip()
    entity_type = request.form.get('entity_type', '')
    entity_id = request.form.get('entity_id', 0, type=int)
    
    if not comment_text or not entity_type or not entity_id:
        return jsonify({'success': False, 'message': 'Invalid parameters'})
    
    # Verify that the entity exists
    entity = None
    if entity_type == 'lead':
        entity = Lead.query.get(entity_id)
        if entity:
            entity_name = f"{entity.first_name} {entity.last_name}"
    elif entity_type == 'deal':
        entity = Deal.query.get(entity_id)
        if entity:
            entity_name = entity.title
    elif entity_type == 'task':
        entity = Task.query.get(entity_id)
        if entity:
            entity_name = entity.title
    
    if not entity:
        return jsonify({'success': False, 'message': f'{entity_type.capitalize()} not found'})
    
    try:
        # Create the comment
        comment = Comment(
            user_id=current_user.id,
            target_type=entity_type,
            target_id=entity_id,
            comment=comment_text,
            created=datetime.utcnow()
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Log activity
        Activity.log(
            action_type='comment_added',
            description=f'Comment added to {entity_type}: {entity_name}',
            user=current_user,
            lead=entity if entity_type == 'lead' else None,
            target_type=entity_type,
            target_id=entity_id,
            data={'comment_id': comment.id, 'comment_text': comment_text[:100]}
        )
        
        # Format the timestamp
        timestamp = comment.created.strftime('%B %d, %Y at %H:%M')
        
        # Return success response
        return jsonify({
            'success': True,
            'comment_id': comment.id,
            'user_name': current_user.username,
            'timestamp': timestamp,
            'comment': comment_text
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}) 