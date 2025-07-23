// Check for task notifications
function checkTaskNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error from API:', data.error);
                return;
            }
            
            if (data.notifications && data.notifications.length > 0) {
                // Show popup for high priority tasks and overdue tasks
                const highPriorityTasks = data.notifications.filter(n => 
                    (n.priority === 'high' || n.is_overdue)
                );
                
                if (highPriorityTasks.length > 0) {
                    // Limit to 3 notifications at a time to avoid overwhelming the user
                    highPriorityTasks.slice(0, 3).forEach(task => {
                        try {
                            // Choose notification type based on task properties
                            let notificationType = 'info';
                            let icon = 'bell';
                            let title = task.title || 'Task Notification';
                            let message = '';
                            
                            if (task.is_overdue && task.priority === 'high') {
                                notificationType = 'danger';
                                icon = 'alert-octagon';
                                message = `Overdue high priority task: ${task.description || 'No description'}`;
                            } else if (task.is_overdue) {
                                notificationType = 'warning';
                                icon = 'alert-triangle';
                                message = `Task is overdue: ${task.time_ago || 'time unknown'}`;
                            } else if (task.priority === 'high') {
                                notificationType = 'warning';
                                icon = 'alert-circle';
                                message = `High priority task due ${task.time_remaining || 'soon'}`;
                            }
                            
                            // Only show if we have a valid URL
                            if (task.url) {
                                toastNotify.show({
                                    title: title,
                                    message: message,
                                    type: notificationType,
                                    icon: icon,
                                    duration: 10000,
                                    actions: [
                                        {
                                            label: 'View Task',
                                            callback: () => window.location.href = task.url
                                        }
                                    ]
                                });
                            }
                        } catch (err) {
                            console.error('Error processing notification:', err, task);
                        }
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error checking for notifications:', error);
        });
}