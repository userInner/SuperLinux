// AI学习网站主JavaScript文件

document.addEventListener('DOMContentLoaded', function() {
    // 移动端菜单切换
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navMenu = document.querySelector('.nav-menu');
    const navActions = document.querySelector('.nav-actions');
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            navMenu.style.display = navMenu.style.display === 'flex' ? 'none' : 'flex';
            navActions.style.display = navActions.style.display === 'flex' ? 'none' : 'flex';
            
            if (navMenu.style.display === 'flex') {
                navMenu.style.flexDirection = 'column';
                navMenu.style.position = 'absolute';
                navMenu.style.top = '100%';
                navMenu.style.left = '0';
                navMenu.style.right = '0';
                navMenu.style.backgroundColor = 'white';
                navMenu.style.padding = '20px';
                navMenu.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
                
                navActions.style.flexDirection = 'column';
                navActions.style.position = 'absolute';
                navActions.style.top = 'calc(100% + 200px)';
                navActions.style.left = '0';
                navActions.style.right = '0';
                navActions.style.backgroundColor = 'white';
                navActions.style.padding = '20px';
                navActions.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            }
        });
    }
    
    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
                
                // 更新导航菜单激活状态
                document.querySelectorAll('.nav-menu a').forEach(link => {
                    link.classList.remove('active');
                });
                this.classList.add('active');
            }
        });
    });
    
    // 导航栏滚动效果
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            // 向下滚动
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // 向上滚动
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop;
        
        // 更新导航菜单激活状态
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-menu a');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            
            if (scrollTop >= sectionTop - 100) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
    
    // 课程卡片点击效果
    document.querySelectorAll('.course-card').forEach(card => {
        card.addEventListener('click', function() {
            const courseTitle = this.querySelector('.course-title').textContent;
            alert(`开始学习: ${courseTitle}`);
        });
    });
    
    // 挑战卡片悬停效果
    document.querySelectorAll('.challenge-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 10px 25px rgba(0,0,0,0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'var(--box-shadow)';
        });
    });
    
    // 订阅表单处理
    const newsletterForm = document.querySelector('.newsletter');
    if (newsletterForm) {
        const emailInput = newsletterForm.querySelector('input[type="email"]');
        const submitBtn = newsletterForm.querySelector('.btn');
        
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const email = emailInput.value.trim();
            
            if (!email) {
                alert('请输入邮箱地址');
                return;
            }
            
            if (!validateEmail(email)) {
                alert('请输入有效的邮箱地址');
                return;
            }
            
            // 模拟订阅成功
            alert('订阅成功！您将收到最新的AI学习资源更新。');
            emailInput.value = '';
        });
    }
    
    // 模拟神经网络动画
    function animateNeuralNetwork() {
        const connections = document.querySelectorAll('.connection');
        let angle = 0;
        
        setInterval(() => {
            angle += 0.02;
            connections.forEach((conn, index) => {
                const length = 100 + Math.sin(angle + index) * 20;
                const rotation = Math.sin(angle + index * 0.5) * 10;
                
                conn.style.width = `${length}px`;
                conn.style.transform = `rotate(${rotation}deg)`;
                conn.style.opacity = 0.5 + Math.sin(angle + index) * 0.3;
            });
        }, 50);
    }
    
    // 启动动画
    setTimeout(animateNeuralNetwork, 1000);
    
    // 邮箱验证函数
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    // 添加页面加载动画
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});