const savedTheme = localStorage.getItem("karumestore-theme") || "light";
document.documentElement.dataset.theme = savedTheme;

document.addEventListener("DOMContentLoaded", () => {

    const themeToggle = document.getElementById("theme-toggle");

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const theme = document.documentElement.dataset.theme === "dark"
                ? "light"
                : "dark";
            document.documentElement.dataset.theme = theme;
            localStorage.setItem("karumestore-theme", theme);
        });
    }

    // Homepage
    loadCategories();
    loadFeaturedProducts();

    // Products page
    loadProductsPage();

    // Cart
    updateCartCount();

    // Search
    setupSearch();

    // Mobile menu
    setupMobileMenu();

});


// ======================================================
// API HELPER
// ======================================================

async function apiRequest(url, options = {}) {

    try {

        const headers = {
            ...(options.headers || {})
        };

        // Check whether the request body is FormData
        const isFormData =
            options.body instanceof FormData;

        // Only set JSON Content-Type for normal requests.
        // Do NOT set it manually for FormData.
        if (
            options.body &&
            !isFormData
        ) {
            headers["Content-Type"] =
                "application/json";
        }

        const response =
            await fetch(
                url,
                {
                    ...options,
                    headers: headers
                }
            );

        const text =
            await response.text();

        let data;

        try {

            data =
                text
                    ? JSON.parse(text)
                    : {};

        } catch {

            throw new Error(
                `Invalid JSON response from ${url}`
            );
        }

        if (!response.ok) {

            throw new Error(
                data.message ||
                data.error ||
                `Request failed with status ${response.status}`
            );
        }

        return data;

    } catch (error) {

        console.error(
            `API Error: ${url}`,
            error
        );

        throw error;
    }
}

// ======================================================
// GET ARRAY FROM API RESPONSE
// ======================================================

function getArray(response, keys = []) {

    if (Array.isArray(response)) {
        return response;
    }

    if (!response || typeof response !== "object") {
        return [];
    }

    if (Array.isArray(response.data)) {
        return response.data;
    }

    for (const key of keys) {

        if (Array.isArray(response[key])) {
            return response[key];
        }
    }

    return [];
}


// ======================================================
// IMAGE HELPER
// ======================================================

function getProductImage(product) {

    if (!product) {
        return "/static/images/no-image.jpg";
    }

    let image = null;

    // Most common fields
    image =
        product.primary_image ||
        product.image_url ||
        product.image ||
        product.thumbnail ||
        null;


    // Images array
    if (!image && Array.isArray(product.images)) {

        const firstImage = product.images[0];

        if (typeof firstImage === "string") {

            image = firstImage;

        } else if (
            firstImage &&
            typeof firstImage === "object"
        ) {

            image =
                firstImage.image_url ||
                firstImage.url ||
                firstImage.image ||
                firstImage.path ||
                null;
        }
    }


    // No image
    if (!image) {

        return "/static/images/no-image.jpg";
    }


    image = String(image).trim();


    // Empty string
    if (!image) {

        return "/static/images/no-image.jpg";
    }


    // If backend returns a relative path
    if (
        !image.startsWith("/") &&
        !image.startsWith("http://") &&
        !image.startsWith("https://") &&
        !image.startsWith("data:")
    ) {

        image = "/" + image;
    }


    return image;
}


// ======================================================
// CATEGORIES
// ======================================================

async function loadCategories() {

    const container =
        document.getElementById("categories-container");

    if (!container) {
        return;
    }

    try {

        container.innerHTML = `
            <div class="loading">
                Loading categories...
            </div>
        `;

        const response =
            await apiRequest("/api/categories");

        const categories =
            getArray(response, ["categories"]);

        if (!categories.length) {

            container.innerHTML = `
                <div class="empty-state">
                    No categories found.
                </div>
            `;

            return;
        }

        container.innerHTML =
            categories.map(category => {

                return `
                    <a
                        href="/products?category=${category.id}"
                        class="category-card"
                    >

                        <div class="category-icon">
                            ${getCategoryIcon(category.name)}
                        </div>

                        <h3>
                            ${escapeHtml(category.name)}
                        </h3>

                        <span>
                            Shop Now →
                        </span>

                    </a>
                `;

            }).join("");

    } catch (error) {

        console.error(
            "Categories error:",
            error
        );

        container.innerHTML = `
            <div class="error-state">
                Failed to load categories.
            </div>
        `;
    }
}


// ======================================================
// FEATURED PRODUCTS
// ======================================================

async function loadFeaturedProducts() {

    const container =
        document.getElementById("featured-products");

    if (!container) {
        return;
    }

    try {

        container.innerHTML = `
            <div class="loading">
                Loading products...
            </div>
        `;

        const response =
            await apiRequest(
                "/api/products/featured"
            );

        const products =
            getArray(response, ["products"]);

        if (!products.length) {

            container.innerHTML = `
                <div class="empty-state">
                    No featured products found.
                </div>
            `;

            return;
        }

        container.innerHTML =
            products
                .map(product =>
                    createProductCard(product)
                )
                .join("");

    } catch (error) {

        console.error(
            "Featured products error:",
            error
        );

        container.innerHTML = `
            <div class="error-state">
                Failed to load products.
            </div>
        `;
    }
}


// ======================================================
// PRODUCTS PAGE
// ======================================================

async function loadProductsPage() {

    const container =
        document.getElementById("products-container") ||
        document.getElementById("products-grid") ||
        document.getElementById("products-list");

    if (!container) {
        return;
    }

    try {

        container.innerHTML = `
            <div class="loading">
                Loading products...
            </div>
        `;


        const params =
            new URLSearchParams(
                window.location.search
            );


        const search =
            params.get("search") || "";


        const category =
            params.get("category") || "";


        const categoryId =
            params.get("category_id") || "";


        const minPrice =
            params.get("min_price") || "";


        const maxPrice =
            params.get("max_price") || "";


        const sort =
            params.get("sort") || "";


        const apiParams =
            new URLSearchParams();


        if (search.trim()) {

            apiParams.set(
                "search",
                search.trim()
            );
        }


        if (category) {

            apiParams.set(
                "category",
                category
            );
        }


        if (categoryId) {

            apiParams.set(
                "category_id",
                categoryId
            );
        }


        if (minPrice) {

            apiParams.set(
                "min_price",
                minPrice
            );
        }


        if (maxPrice) {

            apiParams.set(
                "max_price",
                maxPrice
            );
        }


        if (sort) {

            apiParams.set(
                "sort",
                sort
            );
        }


        const url =
            apiParams.toString()
                ? `/api/products?${apiParams.toString()}`
                : "/api/products";


        console.log(
            "Products API:",
            url
        );


        const response =
            await apiRequest(url);


        let products =
            getArray(response, ["products"]);


        // ==================================================
        // CLIENT SIDE SEARCH
        // ==================================================

        if (search.trim()) {

            const keyword =
                search.trim().toLowerCase();


            products =
                products.filter(product => {

                    const name =
                        String(
                            product.name || ""
                        ).toLowerCase();


                    const description =
                        String(
                            product.description || ""
                        ).toLowerCase();


                    const categoryName =
                        String(
                            product.category?.name || ""
                        ).toLowerCase();


                    return (
                        name.includes(keyword) ||
                        description.includes(keyword) ||
                        categoryName.includes(keyword)
                    );

                });
        }


        // ==================================================
        // CATEGORY FILTER
        // ==================================================

        if (category || categoryId) {

            const selectedCategory =
                Number(
                    categoryId || category
                );


            products =
                products.filter(product => {

                    return Number(
                        product.category?.id ||
                        product.category_id ||
                        0
                    ) === selectedCategory;

                });
        }


        // ==================================================
        // MIN PRICE
        // ==================================================

        if (minPrice) {

            products =
                products.filter(product => {

                    const price =
                        Number(
                            product.discount_price ??
                            product.price ??
                            0
                        );


                    return price >= Number(minPrice);

                });
        }


        // ==================================================
        // MAX PRICE
        // ==================================================

        if (maxPrice) {

            products =
                products.filter(product => {

                    const price =
                        Number(
                            product.discount_price ??
                            product.price ??
                            0
                        );


                    return price <= Number(maxPrice);

                });
        }


        // ==================================================
        // SORT
        // ==================================================

        if (sort === "price_low") {

            products.sort((a, b) => {

                const priceA =
                    Number(
                        a.discount_price ??
                        a.price ??
                        0
                    );


                const priceB =
                    Number(
                        b.discount_price ??
                        b.price ??
                        0
                    );


                return priceA - priceB;

            });
        }


        else if (sort === "price_high") {

            products.sort((a, b) => {

                const priceA =
                    Number(
                        a.discount_price ??
                        a.price ??
                        0
                    );


                const priceB =
                    Number(
                        b.discount_price ??
                        b.price ??
                        0
                    );


                return priceB - priceA;

            });
        }


        else if (sort === "newest") {

            products.sort(
                (a, b) =>
                    Number(b.id) -
                    Number(a.id)
            );
        }


        // ==================================================
        // NO RESULTS
        // ==================================================

        if (!products.length) {

            container.innerHTML = `
                <div class="empty-state">

                    <div style="
                        font-size: 50px;
                        margin-bottom: 15px;
                    ">
                        🔍
                    </div>

                    <h3>
                        No products found
                    </h3>

                    ${
                        search
                            ? `
                                <p>
                                    No products matched
                                    "<strong>
                                        ${escapeHtml(search)}
                                    </strong>".
                                </p>
                              `
                            : `
                                <p>
                                    Try another category
                                    or search.
                                </p>
                              `
                    }

                    <a
                        href="/products"
                        class="btn"
                    >
                        View All Products
                    </a>

                </div>
            `;

            return;
        }


        // ==================================================
        // SHOW PRODUCTS
        // ==================================================

        container.innerHTML =
            products
                .map(product =>
                    createProductCard(product)
                )
                .join("");


        // ==================================================
        // RESULT COUNT
        // ==================================================

        const resultCount =
            document.getElementById(
                "product-result-count"
            );


        if (resultCount) {

            resultCount.textContent =
                `${products.length} product${products.length === 1 ? "" : "s"} found`;
        }


        // ==================================================
        // SEARCH TITLE
        // ==================================================

        const searchTitle =
            document.getElementById(
                "search-results-title"
            );


        if (searchTitle && search) {

            searchTitle.textContent =
                `Search results for "${search}"`;
        }

    } catch (error) {

        console.error(
            "Products page error:",
            error
        );


        container.innerHTML = `
            <div class="error-state">

                <h3>
                    Failed to load products
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>

                <button
                    onclick="location.reload()"
                    class="btn"
                >
                    Try Again
                </button>

            </div>
        `;
    }
}


// ======================================================
// PRODUCT CARD
// ======================================================

function createProductCard(product) {

    // Get product image
    const finalImage =
        getProductImage(product);


    // Price
    const price =
        Number(product.price || 0);


    // Discount
    const discountPrice =
        product.discount_price !== null &&
        product.discount_price !== undefined
            ? Number(product.discount_price)
            : null;


    // Has discount
    const hasDiscount =
        discountPrice !== null &&
        discountPrice < price;


    // Display price
    const displayPrice =
        hasDiscount
            ? discountPrice
            : price;


    // Category
    const categoryName =
        product.category?.name ||
        "Product";


    // Stock
    const stock =
        Number(product.stock || 0);


    return `

        <article class="product-card">

            <a
                href="/product/${product.id}"
                class="product-image-wrapper"
            >

                ${
                    hasDiscount
                        ? `
                            <span class="discount-badge">
                                SALE
                            </span>
                          `
                        : ""
                }


                <img
                    src="${escapeAttribute(finalImage)}"
                    alt="${escapeAttribute(product.name || "Product")}"
                    class="product-image"
                    loading="lazy"
                    onerror="
                        this.onerror=null;
                        this.src='/static/images/no-image.jpg';
                    "
                >

            </a>


            <div class="product-info">


                <span class="product-category">
                    ${escapeHtml(categoryName)}
                </span>


                <h3 class="product-name">

                    <a
                        href="/product/${product.id}"
                    >
                        ${escapeHtml(product.name)}
                    </a>

                </h3>


                <div class="product-price">

                    <strong>
                        ${formatTZS(displayPrice)}
                    </strong>


                    ${
                        hasDiscount
                            ? `
                                <span class="old-price">
                                    ${formatTZS(price)}
                                </span>
                              `
                            : ""
                    }

                </div>


                <div class="product-stock">

                    ${
                        stock > 0
                            ? `
                                <span class="in-stock">
                                    In Stock
                                </span>
                              `
                            : `
                                <span class="out-stock">
                                    Out of Stock
                                </span>
                              `
                    }

                </div>


                <button
                    class="add-cart-btn"
                    onclick="addToCart(${product.id})"
                    ${stock <= 0 ? "disabled" : ""}
                >

                    ${
                        stock > 0
                            ? "Add to Cart"
                            : "Out of Stock"
                    }

                </button>


            </div>

        </article>

    `;
}


// ======================================================
// ADD TO CART
// ======================================================

async function addToCart(
    productId,
    quantity = 1
) {

    try {

        const response =
            await apiRequest(
                "/api/cart/items",
                {
                    method: "POST",

                    body: JSON.stringify({
                        product_id: productId,
                        quantity: quantity
                    })
                }
            );


        console.log(
            "Cart response:",
            response
        );


        alert(
            "Product added to cart!"
        );


        updateCartCount();

    } catch (error) {

        console.error(
            "Add cart error:",
            error
        );


        const message =
            error.message.toLowerCase();


        if (
            message.includes("login") ||
            message.includes("unauthorized") ||
            message.includes("authentication")
        ) {

            alert(
                "Please login first."
            );


            window.location.href =
                "/login";


            return;
        }


        alert(
            error.message ||
            "Failed to add product to cart."
        );
    }
}


// ======================================================
// CART COUNT
// ======================================================
async function updateCartCount() {

    const cartCount =
        document.getElementById(
            "cart-count"
        );


    // =====================================================
    // CART BADGE DOES NOT EXIST
    // =====================================================

    if (!cartCount) {
        return;
    }


    try {

        // =================================================
        // GET CART FROM BACKEND
        // =================================================

        const response =
            await apiRequest(
                "/api/cart"
            );


        // =================================================
        // GET CART OBJECT
        // =================================================

        const cart =
            response?.cart;


        // =================================================
        // CALCULATE TOTAL QUANTITY
        // =================================================

        let count = 0;


        if (
            cart &&
            Array.isArray(cart.items)
        ) {

            count =
                cart.items.reduce(
                    (
                        total,
                        item
                    ) => {

                        return (
                            total +
                            Number(
                                item.quantity || 0
                            )
                        );

                    },
                    0
                );

        }


        // =================================================
        // UPDATE CART BADGE
        // =================================================

        cartCount.textContent =
            count;

    }

    catch (error) {

        console.error(
            "Cart count error:",
            error
        );

        cartCount.textContent =
            "0";

    }

}

// ======================================================
// SEARCH
// ======================================================

function setupSearch() {

    const searchButton =
        document.getElementById(
            "search-button"
        );


    const searchOverlay =
        document.getElementById(
            "search-overlay"
        );


    const closeSearch =
        document.getElementById(
            "close-search"
        );


    const searchInput =
        document.getElementById(
            "search-input"
        );


    const searchForm =
        document.getElementById(
            "search-form"
        );


    // ==================================================
    // OPEN SEARCH
    // ==================================================

    if (
        searchButton &&
        searchOverlay
    ) {

        searchButton.addEventListener(
            "click",
            () => {

                searchOverlay.classList.add(
                    "active"
                );


                if (searchInput) {

                    searchInput.focus();

                }

            }
        );
    }


    // ==================================================
    // CLOSE SEARCH
    // ==================================================

    if (
        closeSearch &&
        searchOverlay
    ) {

        closeSearch.addEventListener(
            "click",
            () => {

                searchOverlay.classList.remove(
                    "active"
                );

            }
        );
    }


    // ==================================================
    // SEARCH SUBMIT
    // ==================================================

    if (searchForm) {

        searchForm.addEventListener(
            "submit",
            event => {

                event.preventDefault();


                if (!searchInput) {
                    return;
                }


                const query =
                    searchInput.value.trim();


                if (!query) {
                    return;
                }


                window.location.href =
                    `/products?search=${encodeURIComponent(query)}`;

            }
        );
    }


    // ==================================================
    // ESC
    // ==================================================

    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape" &&
                searchOverlay
            ) {

                searchOverlay.classList.remove(
                    "active"
                );

            }

        }
    );
}


// ======================================================
// MOBILE MENU
// ======================================================

function setupMobileMenu() {

    const menuButton =
        document.getElementById(
            "mobile-menu-button"
        );


    const mobileMenu =
        document.getElementById(
            "mobile-menu"
        );


    if (
        !menuButton ||
        !mobileMenu
    ) {
        return;
    }


    menuButton.addEventListener(
        "click",
        () => {

            mobileMenu.classList.toggle(
                "active"
            );

        }
    );
}


// ======================================================
// CATEGORY ICONS
// ======================================================

function getCategoryIcon(name) {

    const category =
        String(name || "")
            .toLowerCase();


    if (
        category.includes("cloth")
    ) {
        return "";
    }


    if (
        category.includes("shoe")
    ) {
        return "";
    }


    if (
        category.includes("fridge") ||
        category.includes("refrigerator")
    ) {
        return "";
    }


    if (
        category.includes("electronic")
    ) {
        return "";
    }


    if (
        category.includes("bag")
    ) {
        return "";
    }


    if (
        category.includes("watch")
    ) {
        return "";
    }


    if (
        category.includes("accessor")
    ) {
        return "";
    }


    if (
        category.includes("appliance")
    ) {
        return "";
    }


    return "";
}


// ======================================================
// CURRENCY
// ======================================================

function formatTZS(amount) {

    const number =
        Number(amount || 0);


    return new Intl.NumberFormat(
        "en-TZ",
        {
            style: "currency",
            currency: "TZS",
            maximumFractionDigits: 0
        }
    ).format(number);
}


// ======================================================
// SECURITY HELPERS
// ======================================================

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }


    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}


function escapeAttribute(value) {

    return escapeHtml(value);
}


// =====================================================
// LOGIN
// =====================================================

const loginForm = document.getElementById("login-form");


if (loginForm) {

    loginForm.addEventListener("submit", async function (e) {

        e.preventDefault();


        const message =
            document.getElementById("form-message");


        const email =
            document.getElementById("email").value.trim();


        const password =
            document.getElementById("password").value;


        // =============================================
        // CHECK EMPTY FIELDS
        // =============================================

        if (!email && !password) {

            message.textContent =
                "Email and password are required.";

            return;
        }


        if (!email) {

            message.textContent =
                "Email is required.";

            return;
        }


        if (!password) {

            message.textContent =
                "Password is required.";

            return;
        }


        // =============================================
        // SEND LOGIN REQUEST
        // =============================================

        try {

            const data = await apiRequest(
                "/api/auth/login",
                {
                    method: "POST",

                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );


            // =========================================
            // SUCCESS
            // =========================================

            if (data.success) {

                if (data.user.role === "admin") {

                    location.href = "/admin";

                } else {

                    location.href = "/products";

                }

                return;
            }


            // =========================================
            // BACKEND MESSAGE
            // =========================================

            message.textContent =
                data.message || "Login failed.";

        }


        // =============================================
        // ERROR
        // =============================================

        catch (error) {

            console.error(
                "Login error:",
                error
            );


            message.textContent =
                error.message ||
                "Invalid credentials.";

        }

    });

}

// =====================================================
// FORGOT PASSWORD
// =====================================================

const forgotPasswordForm =
    document.getElementById("forgot-password-form");


if (forgotPasswordForm) {

    forgotPasswordForm.addEventListener(
        "submit",
        async function (e) {

            e.preventDefault();


            const message =
                document.getElementById("forgot-message");


            const email =
                document
                    .getElementById("forgot-email")
                    .value
                    .trim();


            // =========================================
            // CHECK EMAIL
            // =========================================

            if (!email) {

                message.textContent =
                    "Email is required.";

                return;
            }

            // ================main otp=================
            // =========================================
            // SEND OTP REQUEST
            // =========================================

            try {

                const data = await apiRequest(
                    "/api/auth/forgot-password",
                    {
                        method: "POST",

                        body: JSON.stringify({
                            email: email
                        })
                    }
                );


                // =====================================
                // SUCCESS
                // =====================================

                if (data.success) {

                message.textContent =
                    data.message ||
                    "OTP has been sent.";

                message.style.color = "green";
                setTimeout(() => {

                    location.href =
                        "/verify-otp";

                }, 700);

                return;
                }


                // =====================================
                // BACKEND MESSAGE
                // =====================================

                message.textContent =
                    data.message ||
                    "Unable to send OTP.";

            }


            // =========================================
            // ERROR
            // =========================================

            catch (error) {

                console.error(
                    "Forgot password error:",
                    error
                );


                message.textContent =
                    error.message ||
                    "Unable to send OTP.";

            }

        }
    );

}


// =====================================================
// RESET PASSWORD
// =====================================================

const resetPasswordForm =
    document.getElementById("reset-password-form");


if (resetPasswordForm) {

    resetPasswordForm.addEventListener(
        "submit",
        async function (e) {

            e.preventDefault();


            const message =
                document.getElementById("reset-message");


            const password =
                document
                    .getElementById("new-password")
                    .value;


            const confirmPassword =
                document
                    .getElementById("confirm-password")
                    .value;


            // =========================================
            // CHECK PASSWORD
            // =========================================

            if (!password || !confirmPassword) {

                message.textContent =
                    "Password and confirmation are required.";

                return;
            }


            // =========================================
            // CHECK MATCH
            // =========================================

            if (password !== confirmPassword) {

                message.textContent =
                    "Passwords do not match.";

                return;
            }


            // =========================================
            // SEND REQUEST
            // =========================================

            try {

                const data = await apiRequest(
                    "/api/auth/reset-password",
                    {
                        method: "POST",

                        body: JSON.stringify({
                            password: password,
                            confirm_password: confirmPassword
                        })
                    }
                );


                if (data.success) {

                    message.textContent =
                        data.message ||
                        "Password reset successfully.";

                    message.style.color = "green";
                    setTimeout(() => {

                        location.href = "/login";

                    }, 1500);

                    return;
                }


                message.textContent =
                    data.message ||
                    "Password reset failed.";

            }


            catch (error) {

                console.error(
                    "Reset password error:",
                    error
                );


                message.textContent =
                    error.message ||
                    "Password reset failed.";

            }

        }
    );

}

// =====================================================
// VERIFY OTP
// =====================================================

const verifyOtpForm =
    document.getElementById("verify-otp-form");


if (verifyOtpForm) {

    verifyOtpForm.addEventListener(
        "submit",
        async function (e) {

            e.preventDefault();


            const message =
                document.getElementById("verify-message");


            const email =
                document
                    .getElementById("verify-email")
                    .value
                    .trim()
                    .toLowerCase();


            const otp =
                document
                    .getElementById("otp")
                    .value
                    .trim();


            // =========================================
            // CHECK EMAIL
            // =========================================

            if (!email) {

                message.textContent =
                    "Email is required.";

                return;
            }


            // =========================================
            // CHECK OTP
            // =========================================

            if (!otp) {

                message.textContent =
                    "OTP is required.";

                return;
            }


            if (!/^\d{6}$/.test(otp)) {

                message.textContent =
                    "OTP must be 6 digits.";

                return;
            }


            // =========================================
            // VERIFY OTP
            // =========================================

            try {

                const data = await apiRequest(
                    "/api/auth/verify-otp",
                    {
                        method: "POST",

                        body: JSON.stringify({
                            email: email,
                            otp: otp
                        })
                    }
                );


                // =====================================
                // SUCCESS
                // =====================================

               if (data.success) {

                    message.textContent =
                        data.message ||
                        "OTP verified successfully.";
                
                    message.style.color = "green";
                
                    setTimeout(() => {
                
                        location.href =
                            "/reset-password";
                
                    }, 700);
                
                    return;
                }


                // =====================================
                // BACKEND MESSAGE
                // =====================================

                message.textContent =
                    data.message ||
                    "OTP verification failed.";

            }


            // =========================================
            // ERROR
            // =========================================

            catch (error) {

                console.error(
                    "OTP verification error:",
                    error
                );


                message.textContent =
                    error.message ||
                    "OTP verification failed.";

            }

        }
    );

}

// =====================================================
// ADMIN DELETE PRODUCT
// =====================================================

async function deleteProduct(
    productId,
    productName
) {

    alert(
        "DELETE FUNCTION IS WORKING"
    );

    console.log(
        "Delete product clicked:",
        productId,
        productName
    );

    // ...

    // =================================================
    // CONFIRM DELETE
    // =================================================

    const confirmed =
        confirm(
            `Are you sure you want to delete "${productName}"?`
        );


    if (!confirmed) {

        return;

    }


    // =================================================
    // SEND DELETE REQUEST
    // =================================================

    try {

        const data =
            await apiRequest(
                `/api/admin/products/${productId}`,
                {
                    method: "DELETE"
                }
            );


        console.log(
            "Delete response:",
            data
        );


        // =================================================
        // CHECK RESPONSE
        // =================================================

        if (!data?.success) {

            alert(
                data?.message ||
                "Unable to delete product."
            );

            return;

        }


        // =================================================
        // SUCCESS
        // =================================================

        alert(
            "Product deleted successfully."
        );


        // =================================================
        // RELOAD PRODUCT MANAGEMENT PAGE
        // =================================================

        window.location.reload();


    } catch (error) {

        console.error(
            "Delete product error:",
            error
        );


        alert(
            error.message ||
            "Unable to delete product."
        );

    }

}
