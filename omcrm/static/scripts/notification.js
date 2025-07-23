document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const notificationBell = document.getElementById('notification-bell');
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationList = document.getElementById('notification-list');
    const notificationCount = document.getElementById('notification-count');
    const closeNotifications = document.getElementById('close-notifications');
    
    // Fetch notification count
    function fetchNotificationCount() {
        fetch('/api/notifications/count')
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    notificationCount.textContent = data.count;
                    notificationCount.style.display = 'flex';
                } else {
                    notificationCount.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error fetching notification count:', error);
            });
    }
    
    // Fetch notifications
    function fetchNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                notificationList.innerHTML = ''; // Clear existing notifications
                
                if (data.error) {
                    notificationList.innerHTML = `
                        <div class="text-center py-4">
                            <p class="text-muted mb-0">${data.error}</p>
                        </div>
                    `;
                    return;
                }
                
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(notification => {
                        const notificationItem = document.createElement('div');
                        notificationItem.className = 'notification-item' + (notification.is_read ? '' : ' unread');
                        notificationItem.setAttribute('data-id', notification.id);
                        notificationItem.setAttribute('data-url', notification.url || '#');
                        
                        // Create notification content
                        notificationItem.innerHTML = `
                            <div class="notification-title ${notification.priority ? 'priority-' + notification.priority : ''}">
                                ${notification.title}
                            </div>
                            <div class="notification-description">
                                ${notification.description || ''}
                            </div>
                            <div class="notification-time">
                                ${notification.time_ago || notification.time_remaining || ''}
                            </div>
                        `;
                        
                        // Make notification clickable
                        notificationItem.addEventListener('click', function() {
                            const url = this.getAttribute('data-url');
                            if (url && url !== '#') {
                                window.location.href = url;
                            }
                        });
                        
                        notificationList.appendChild(notificationItem);
                    });
                } else {
                    notificationList.innerHTML = `
                        <div class="text-center py-4">
                            <p class="text-muted mb-0">No notifications</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error fetching notifications:', error);
                notificationList.innerHTML = `
                    <div class="text-center py-4">
                        <p class="text-muted mb-0">Failed to load notifications</p>
                    </div>
                `;
            });
    }
    
    // Toggle notification dropdown
    if (notificationBell) {
        notificationBell.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const isVisible = notificationDropdown.style.display === 'block';
            
            if (!isVisible) {
                notificationDropdown.style.display = 'block';
                fetchNotifications();
            } else {
                notificationDropdown.style.display = 'none';
            }
        });
    }
    
    // Close notifications dropdown
    if (closeNotifications) {
        closeNotifications.addEventListener('click', function() {
            notificationDropdown.style.display = 'none';
        });
    }
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (notificationDropdown && 
            notificationDropdown.style.display === 'block' && 
            !notificationDropdown.contains(e.target) && 
            e.target !== notificationBell) {
            notificationDropdown.style.display = 'none';
        }
    });
    
    // Mock API for notifications if needed
    if (!window.location.pathname.includes('/webtrader')) {
        // Only fetch if we're not in webtrader page
        fetchNotificationCount();
        
        // Refresh notification count periodically
        setInterval(fetchNotificationCount, 60000); // Every minute
    }
}); 