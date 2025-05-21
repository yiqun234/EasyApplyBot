document.addEventListener('DOMContentLoaded', function() {
    // 解析URL参数
    function getURLParameter(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }

    // 获取当前语言参数
    const langParam = getURLParameter('lang');
    let currentLang = localStorage.getItem('language') || 'en';
    
    // 如果URL中有语言参数，则使用该参数
    if (langParam && (langParam === 'en' || langParam === 'zh')) {
        currentLang = langParam;
        localStorage.setItem('language', currentLang);
    }

    // 设置语言
    setLanguage(currentLang);

    // 更新所有链接，添加语言参数
    function updateLinks() {
        const links = document.querySelectorAll('a[href]');
        links.forEach(link => {
            const href = link.getAttribute('href');
            // 不处理外部链接或锚点链接
            if (href.startsWith('http') || href.startsWith('#') || href.includes('?')) {
                return;
            }
            // 添加语言参数
            link.setAttribute('href', `${href}?lang=${currentLang}`);
        });
    }

    // 语言切换按钮点击事件
    const langSwitcher = document.getElementById('lang-switcher');
    if (langSwitcher) {
        langSwitcher.addEventListener('click', function() {
            switchLanguage();
        });
    }

    // 移动版语言切换按钮
    const mobileLangSwitcher = document.getElementById('mobile-lang-switcher');
    if (mobileLangSwitcher) {
        mobileLangSwitcher.addEventListener('click', function() {
            switchLanguage();
        });
    }

    // 语言切换功能
    function switchLanguage() {
        const newLang = currentLang === 'en' ? 'zh' : 'en';
        localStorage.setItem('language', newLang);
        // 使用语言参数刷新页面
        window.location.href = window.location.pathname + '?lang=' + newLang;
    }

    // 设置语言显示
    function setLanguage(lang) {
        currentLang = lang;
        document.querySelectorAll('[data-lang-en], [data-lang-zh]').forEach(el => {
            if (lang === 'en') {
                if (el.tagName.toLowerCase() === 'span' || el.tagName.toLowerCase() === 'p' || el.tagName.toLowerCase() === 'li' || el.tagName.toLowerCase() === 'td' || el.tagName.toLowerCase() === 'th') {
                    el.innerHTML = el.getAttribute('data-lang-en');
                } else {
                    el.textContent = el.getAttribute('data-lang-en');
                }
            } else {
                if (el.tagName.toLowerCase() === 'span' || el.tagName.toLowerCase() === 'p' || el.tagName.toLowerCase() === 'li' || el.tagName.toLowerCase() === 'td' || el.tagName.toLowerCase() === 'th') {
                    el.innerHTML = el.getAttribute('data-lang-zh');
                } else {
                    el.textContent = el.getAttribute('data-lang-zh');
                }
            }
        });

        // 切换流程图显示
        const workflowEn = document.getElementById('workflow-en');
        const workflowZh = document.getElementById('workflow-zh');
        
        if (workflowEn && workflowZh) {
            if (lang === 'en') {
                workflowEn.style.display = 'inline-block';
                workflowZh.style.display = 'none';
            } else {
                workflowEn.style.display = 'none';
                workflowZh.style.display = 'inline-block';
            }
        }

        // 更新切换按钮文本
        const switcherBtn = document.getElementById('lang-switcher');
        if (switcherBtn) {
            switcherBtn.textContent = lang === 'en' ? '切换中文' : 'Switch to English';
        }
        
        // 更新移动版切换按钮文本
        const mobileSwitcherBtn = document.getElementById('mobile-lang-switcher');
        if (mobileSwitcherBtn) {
            mobileSwitcherBtn.textContent = lang === 'en' ? '切换中文' : 'Switch to English';
        }

        // 更新链接以包含语言参数
        updateLinks();
    }

    // 移动菜单按钮 - 修复点击问题
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // 切换菜单显示状态
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                document.body.classList.remove('menu-open');
            } else {
                navLinks.classList.add('active');
                document.body.classList.add('menu-open');
            }
        });
    }
    
    // 点击菜单链接后关闭菜单
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                navLinks.classList.remove('active');
                document.body.classList.remove('menu-open');
            }
        });
        });

    // 监听窗口大小变化，在大屏幕下关闭菜单
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            navLinks.classList.remove('active');
            document.body.classList.remove('menu-open');
        }
    });

    // FAQ折叠面板
    const faqItems = document.querySelectorAll('.faq-item');
    if (faqItems.length) {
        faqItems.forEach(item => {
            const questionEl = item.querySelector('.faq-question');
            questionEl.addEventListener('click', function() {
                item.classList.toggle('active');
            });
        });
    }

    // 添加动画效果
    const animateElements = document.querySelectorAll('.feature-card, .step');
    if (animateElements.length) {
        animateElements.forEach(el => {
            el.classList.add('animate-element');
        });

        // 监听滚动，触发动画
        const checkScroll = function() {
            animateElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                const windowHeight = window.innerHeight;
                if (rect.top < windowHeight * 0.85) {
                    el.classList.add('animate-in');
                }
            });
        };

        window.addEventListener('scroll', checkScroll);
        checkScroll(); // 初始检查
    }

    // 关闭菜单点击文档其他地方
    document.addEventListener('click', function(event) {
        if (navLinks && navLinks.classList.contains('active')) {
            if (!navLinks.contains(event.target) && !mobileMenuBtn.contains(event.target)) {
                navLinks.classList.remove('active');
                document.body.classList.remove('menu-open');
            }
        }
    });

    // 调用处理URL锚点的函数
    handleHashNavigation();
});

// 添加动画效果
function initAnimations() {
    // 获取所有需要动画的元素
    const animateElements = document.querySelectorAll('.animate-element');
    
    // 创建Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                // 如果元素已经动画完成，可以取消观察
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1 // 当10%的元素可见时触发
    });
    
    // 观察所有动画元素
    animateElements.forEach(element => {
        observer.observe(element);
    });
}

// 平滑滚动到锚点
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// 移动端菜单切换
function initMobileMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            document.body.classList.toggle('menu-open');
            navLinks.classList.toggle('active');
        });
    }
    
    // 点击菜单链接后关闭菜单
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                document.body.classList.remove('menu-open');
                navLinks.classList.remove('active');
            }
        });
    });
}

// 检测滚动位置，添加导航栏背景
function initScrollDetection() {
    const nav = document.querySelector('nav');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });
} 

// 处理URL中的锚点跳转，特别是从其他页面跳转过来的情况
function handleHashNavigation() {
    // 检查URL是否包含锚点
    let targetId = window.location.hash;
    
    // 如果URL中没有锚点，检查是否有存储的滚动目标
    if (!targetId && sessionStorage.getItem('scrollTarget')) {
        targetId = sessionStorage.getItem('scrollTarget');
        console.log("从sessionStorage获取到滚动目标:", targetId);
        // 清除存储的滚动目标，避免下次访问时还使用它
        sessionStorage.removeItem('scrollTarget');
    }
    
    if (targetId) {
        console.log("准备滚动到目标:", targetId);
        
        // 使用更长的延迟确保页面完全加载
        setTimeout(function() {
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                console.log("找到目标元素，准备滚动到:", targetId);
                // 平滑滚动到目标位置，考虑导航栏高度
                const navHeight = document.querySelector('nav').offsetHeight;
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;
                
                console.log("滚动到位置:", targetPosition, "导航栏高度:", navHeight);
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // 额外保障措施：再次尝试滚动
                setTimeout(function() {
                    const newTargetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;
                    console.log("再次滚动到位置:", newTargetPosition);
                    window.scrollTo({
                        top: newTargetPosition,
                        behavior: 'smooth'
                    });
                }, 1000);
            } else {
                console.log("未找到目标元素:", targetId);
            }
        }, 500);
    }
} 