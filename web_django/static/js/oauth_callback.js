// Script để đóng popup OAuth sau khi đăng nhập thành công
(function() {
    console.log('[CALLBACK] Attempting to close popup...');
    
    // Thử đóng ngay lập tức
    function attemptClose() {
        try {
            window.close();
            console.log('[CALLBACK] window.close() called');
        } catch (e) {
            console.error('[CALLBACK] Error closing window:', e);
        }
    }
    
    // Thử đóng nhiều lần
    let attempts = 0;
    const maxAttempts = 10;
    
    const closeInterval = setInterval(function() {
        attempts++;
        console.log('[CALLBACK] Close attempt #' + attempts);
        attemptClose();
        
        if (attempts >= maxAttempts) {
            clearInterval(closeInterval);
            console.log('[CALLBACK] Max attempts reached, showing message to user');
            
            // Nếu không đóng được, thêm button để user tự đóng
            const container = document.querySelector('.container');
            if (container) {
                container.innerHTML += '<button onclick="window.close()" style="margin-top:20px;padding:10px 20px;background:white;color:#667eea;border:none;border-radius:5px;cursor:pointer;font-size:16px;font-weight:bold;">Đóng cửa sổ</button>';
            }
        }
    }, 200);
    
})();
