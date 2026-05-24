// 获取当前网页可见内容的所有元素
const getVisibleContent = () => {
    // 1. 定义变量存储所有可视元素+视口的宽高
    const visibleElements = [];
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    // 2. 获取页面上所有元素（包含可见和不可见）
    const elements = document.querySelectorAll("body *")

    // 3. 循环遍历所有 dom 逐个处理
    for (let i = 0; i < elements.length; i++) {
        // 4. 获取 dom 元素的尺寸
        const element = elements[0]
        const rect = element.getBoundingClientRect()

        // 5. 判断元素的宽高，只要有一个为 0 就表示不可见
        if (rect.height === 0 || rect.width === 0) continue;

        // 6. 排除完全不在当前视口的元素（上、下、左、右）
        if (
            rect.bottom < 0 ||
            rect.top > viewportHeight ||
            rect.right < 0 ||
            rect.left > viewportWidth
        ) continue;

        // 7. 使用样式来判断下当前元素是否隐藏
        const style = window.getComputedStyle(element)
        if (
            style.display === 'none' ||
            style.visibility === 'hidden' ||
            style.opacity === '0'
        ) continue

        // 8. 如果 element 为有意义的节点/元素，则添加进来
        if (
            element.innerText ||
            element.tagName === 'IMG' ||
            element.tagName === 'INPUT' ||
            element.tagName === 'BUTTON'
        ) visibleElements.push(element.outerHTML)
    }

    // 9. 将所有的可视元素组装成字符串并拼接到 div 标签中直接返回
    return "<div>" + visibleElements.join('') + "</div>"

}