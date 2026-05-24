// Frontend Logic for KulkasPintar AI Web MVP

// State variables
let token = localStorage.getItem("kp_auth_token") || null;
let currentUser = null;
let currentInventory = [];
let activeRoom = null;
let detectedIngredients = [];
let pendingRoomId = null;

// DOM Elements
const authView = document.getElementById("auth-view");
const dashboardView = document.getElementById("dashboard-view");
const authForm = document.getElementById("auth-form");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const authBtnText = document.getElementById("auth-btn-text");

const userEmailDisplay = document.getElementById("user-email-display");
const btnLogout = document.getElementById("btn-logout");

const roomStatus = document.getElementById("room-status");
const roomIdDisplay = document.getElementById("room-id-display");
const roomMembersCount = document.getElementById("room-members-count");
const btnLeaveRoom = document.getElementById("btn-leave-room");
const btnJoinRoomModal = document.getElementById("btn-join-room-modal");

const btnEditDiet = document.getElementById("btn-edit-diet");
const dietaryBadges = document.getElementById("dietary-badges");
const dietModal = document.getElementById("diet-modal");
const dietForm = document.getElementById("diet-form");
const btnCloseDiet = document.getElementById("btn-close-diet");

const toggleStrictMatch = document.getElementById("toggle-strict-match");
const toggleSaveFood = document.getElementById("toggle-save-food");

const scanUploadModal = document.getElementById("scan-upload-modal");
const btnOpenScan = document.getElementById("btn-open-scan");
const btnCloseScanModal = document.getElementById("btn-close-scan-modal");

const dropzone = document.getElementById("dropzone");
const fileUpload = document.getElementById("file-upload");

const btnAddItemModal = document.getElementById("btn-add-item-modal");
const addItemModal = document.getElementById("add-item-modal");
const addItemForm = document.getElementById("add-item-form");
const btnCloseAddItem = document.getElementById("btn-close-add-item");

const joinRoomModal = document.getElementById("join-room-modal");
const joinRoomForm = document.getElementById("join-room-form");
const roomInputId = document.getElementById("room-input-id");
const btnCloseRoom = document.getElementById("btn-close-room");
const btnGenerateRoom = document.getElementById("btn-generate-room");

const confirmLoggingModal = document.getElementById("confirm-logging-modal");
const confirmItemsTbody = document.getElementById("confirm-items-tbody");
const btnCancelLogging = document.getElementById("btn-cancel-logging");
const btnSaveLogging = document.getElementById("btn-save-logging");

const inventoryList = document.getElementById("inventory-list");
const recipesEmptyState = document.getElementById("recipes-empty-state");
const recipesContainer = document.getElementById("recipes-container");

const globalLoader = document.getElementById("global-loader");
const toastContainer = document.getElementById("toast-container");

// API helper functions
async function apiRequest(endpoint, method = "GET", body = null, isMultipart = false) {
    const headers = {};
    if (!isMultipart) {
        headers["Content-Type"] = "application/json";
    }

    const config = {
        method,
        headers
    };

    if (body) {
        config.body = isMultipart ? body : JSON.stringify(body);
    }

    try {
        const response = await fetch(endpoint, config);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "An error occurred");
        }
        return data;
    } catch (err) {
        showToast(err.message, "error");
        throw err;
    }
}

// Toast Notifications helper
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg transition duration-300 transform translate-x-12 opacity-0 text-xs font-semibold max-w-sm `;
    
    let icon = "";
    if (type === "success") {
        toast.className += "bg-emerald-50 border border-emerald-200 text-emerald-800";
        icon = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>`;
    } else if (type === "error") {
        toast.className += "bg-rose-50 border border-rose-200 text-rose-800";
        icon = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>`;
    } else {
        toast.className += "bg-white border border-slate-200 text-teal-700 shadow-sm";
        icon = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`;
    }

    toast.innerHTML = `${icon}<span>${message}</span>`;
    toastContainer.appendChild(toast);

    // Fade in
    setTimeout(() => {
        toast.classList.remove("translate-x-12", "opacity-0");
    }, 10);

    // Fade out and remove
    setTimeout(() => {
        toast.classList.add("translate-x-12", "opacity-0");
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// Expiration Status Calculator (Natively in JS)
function calculateExpirationStatus(addedAtStr, expiresAtStr) {
    const now = new Date();
    let expiryDate;

    if (expiresAtStr) {
        expiryDate = new Date(expiresAtStr);
    } else {
        // Fallback: estimate 7 days shelf life from addition time
        const addedDate = new Date(addedAtStr);
        expiryDate = new Date(addedDate.getTime() + 7 * 24 * 60 * 60 * 1000);
    }

    const diffTime = expiryDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 0) {
        return { label: "Expired", class: "tag-expired", daysText: "Expired" };
    } else if (diffDays <= 2) {
        return { label: "Use Soon", class: "tag-warning", daysText: `Expires in ${diffDays}d` };
    } else {
        return { label: "Fresh", class: "tag-fresh", daysText: `${diffDays} days left` };
    }
}

// Auth flow actions
let isLoginMode = true;
tabLogin.addEventListener("click", () => {
    isLoginMode = true;
    tabLogin.className = "flex-1 pb-3 text-center border-b-2 border-teal-600 font-semibold text-teal-600 transition";
    tabRegister.className = "flex-1 pb-3 text-center border-b-2 border-transparent font-medium text-slate-550 hover:text-slate-800 transition";
    authBtnText.innerText = "Log In";
});

tabRegister.addEventListener("click", () => {
    isLoginMode = false;
    tabRegister.className = "flex-1 pb-3 text-center border-b-2 border-teal-600 font-semibold text-teal-600 transition";
    tabLogin.className = "flex-1 pb-3 text-center border-b-2 border-transparent font-medium text-slate-550 hover:text-slate-800 transition";
    authBtnText.innerText = "Register Profile";
});

authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        if (isLoginMode) {
            const res = await apiRequest("/api/v1/auth/login", "POST", { email, password });
            token = res.access_token;
            localStorage.setItem("kp_auth_token", token);
            showToast("Log in successful!", "success");
        } else {
            await apiRequest("/api/v1/auth/register", "POST", { email, password });
            // Automatically log in
            const res = await apiRequest("/api/v1/auth/login", "POST", { email, password });
            token = res.access_token;
            localStorage.setItem("kp_auth_token", token);
            showToast("Registration successful!", "success");
        }
        initDashboard();
    } catch (err) {
        console.error("Auth failed:", err);
    }
});

btnLogout.addEventListener("click", () => {
    token = null;
    currentUser = null;
    localStorage.removeItem("kp_auth_token");
    authView.classList.remove("hidden");
    dashboardView.classList.add("hidden");
    showToast("Signed out successfully.", "info");
});

// App Initialization
async function initDashboard() {
    if (!token) {
        authView.classList.remove("hidden");
        dashboardView.classList.add("hidden");
        return;
    }

    try {
        // Fetch current user details
        currentUser = await apiRequest(`/api/v1/auth/me?token=${token}`);
        
        userEmailDisplay.innerText = currentUser.email;
        authView.classList.add("hidden");
        dashboardView.classList.remove("hidden");

        // Render profile restrictions
        renderDietaryProfile();

        // Fetch Room status
        await fetchRoomStatus();

        // Fetch Inventory
        await fetchInventory();

        // Check if there was a pending room join request from link
        if (pendingRoomId) {
            const rId = pendingRoomId;
            pendingRoomId = null;
            await joinCollaborativeRoom(rId);
        }
    } catch (err) {
        console.error("Dashboard initialization failed:", err);
        // Token is invalid, reset
        token = null;
        localStorage.removeItem("kp_auth_token");
        authView.classList.remove("hidden");
        dashboardView.classList.add("hidden");
    }
}

// Dietary Profile Manager
function renderDietaryProfile() {
    dietaryBadges.innerHTML = "";
    if (!currentUser.dietary_restrictions || currentUser.dietary_restrictions.length === 0) {
        dietaryBadges.innerHTML = `<span class="text-xs text-slate-500 italic">No restrictions saved.</span>`;
        return;
    }

    currentUser.dietary_restrictions.forEach(restriction => {
        const badge = document.createElement("span");
        badge.className = "text-[10px] px-2.5 py-1 bg-teal-50 border border-teal-200/60 text-teal-700 font-bold rounded-full shadow-sm";
        badge.innerText = restriction;
        dietaryBadges.appendChild(badge);
    });
}

btnEditDiet.addEventListener("click", () => {
    // Check checkboxes
    const checkboxes = dietForm.querySelectorAll("input[name='restrictions']");
    checkboxes.forEach(cb => {
        cb.checked = currentUser.dietary_restrictions.includes(cb.value);
    });
    dietModal.classList.remove("hidden");
});

btnCloseDiet.addEventListener("click", () => {
    dietModal.classList.add("hidden");
});

dietForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const checked = Array.from(dietForm.querySelectorAll("input[name='restrictions']:checked")).map(cb => cb.value);

    try {
        currentUser = await apiRequest(`/api/v1/auth/profile?token=${token}`, "PUT", {
            dietary_restrictions: checked
        });
        renderDietaryProfile();
        showToast("Dietary profile updated!", "success");
        dietModal.classList.add("hidden");
    } catch (err) {
        console.error("Update profile failed:", err);
    }
});

// Collaborative Room actions
async function fetchRoomStatus() {
    try {
        activeRoom = await apiRequest(`/api/v1/rooms/active?token=${token}`);
        if (activeRoom.in_room) {
            roomStatus.classList.remove("hidden");
            roomIdDisplay.innerText = activeRoom.room_id;
            roomMembersCount.innerText = `(${activeRoom.members.length} members)`;
            btnJoinRoomModal.innerText = "Switch Room";
        } else {
            roomStatus.classList.add("hidden");
            btnJoinRoomModal.innerText = "Connect Room";
        }
    } catch (err) {
        console.error("Failed to fetch room status:", err);
    }
}

btnJoinRoomModal.addEventListener("click", () => {
    joinRoomModal.classList.remove("hidden");
});

btnCloseRoom.addEventListener("click", () => {
    joinRoomModal.classList.add("hidden");
});

btnGenerateRoom.addEventListener("click", () => {
    const randId = Math.random().toString(36).substring(2, 8);
    roomInputId.value = randId;
});

joinRoomForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const rId = roomInputId.value.trim().toLowerCase();
    if (!rId) return;

    await joinCollaborativeRoom(rId);
    joinRoomModal.classList.add("hidden");
});

async function joinCollaborativeRoom(roomId) {
    try {
        await apiRequest(`/api/v1/rooms/join?token=${token}`, "POST", { room_id: roomId });
        showToast(`Joined shared room: ${roomId}`, "success");
        
        // Rewrite URL address bar to reflect room ID dynamically for easy sharing
        history.pushState(null, "", `/room/${roomId}`);
        
        await fetchRoomStatus();
        await fetchInventory();
    } catch (err) {
        console.error("Failed to join room:", err);
    }
}

btnLeaveRoom.addEventListener("click", async () => {
    try {
        await apiRequest(`/api/v1/rooms/leave?token=${token}`, "POST");
        showToast("Left collaborative room session.", "info");
        
        // Revert URL address bar
        history.pushState(null, "", "/");
        
        await fetchRoomStatus();
        await fetchInventory();
    } catch (err) {
        console.error("Failed to leave room:", err);
    }
});

// Inventory CRUD actions
async function fetchInventory() {
    try {
        currentInventory = await apiRequest(`/api/v1/inventory?token=${token}`);
        renderInventoryList();
    } catch (err) {
        console.error("Failed to fetch inventory:", err);
    }
}

function renderInventoryList() {
    inventoryList.innerHTML = "";
    if (currentInventory.length === 0) {
        inventoryList.innerHTML = `
            <tr>
                <td colspan="5" class="py-12 text-center text-slate-500 text-xs">
                    Your inventory is empty. Add items manually or upload a picture.
                </td>
            </tr>
        `;
        return;
    }

    currentInventory.forEach(item => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-200 hover:bg-slate-50 text-xs transition duration-200 text-slate-700";

        // Expiration details
        const exp = calculateExpirationStatus(item.added_at, item.expires_at);

        tr.innerHTML = `
            <td class="py-4 px-4 font-bold text-slate-800">${item.name}</td>
            <td class="py-4 px-4 text-slate-550">${item.category}</td>
            <td class="py-4 px-4 text-center font-semibold text-slate-700">
                <div class="flex items-center justify-center gap-2">
                    <button class="btn-dec w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 active:scale-95 text-slate-700 font-bold transition flex items-center justify-center cursor-pointer" data-id="${item.id}" data-qty="${item.quantity}">-</button>
                    <span class="w-8 inline-block text-center font-mono">${item.quantity} ${item.unit}</span>
                    <button class="btn-inc w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 active:scale-95 text-slate-700 font-bold transition flex items-center justify-center cursor-pointer" data-id="${item.id}" data-qty="${item.quantity}">+</button>
                </div>
            </td>
            <td class="py-4 px-4">
                <div class="flex items-center gap-2">
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${exp.class}">${exp.label}</span>
                    <span class="text-[10px] text-slate-500 font-medium">${exp.daysText}</span>
                </div>
            </td>
            <td class="py-4 px-4 text-right">
                <button class="btn-delete text-rose-650 hover:text-rose-800 font-semibold cursor-pointer" data-id="${item.id}">Delete</button>
            </td>
        `;

        // Listeners for quantity adjusters
        tr.querySelector(".btn-inc").addEventListener("click", () => adjustQuantity(item.id, item.quantity + 1));
        tr.querySelector(".btn-dec").addEventListener("click", () => {
            if (item.quantity <= 1) {
                deleteItem(item.id);
            } else {
                adjustQuantity(item.id, item.quantity - 1);
            }
        });
        tr.querySelector(".btn-delete").addEventListener("click", () => deleteItem(item.id));

        inventoryList.appendChild(tr);
    });
}

async function adjustQuantity(itemId, newQty) {
    try {
        await apiRequest(`/api/v1/inventory/${itemId}?token=${token}`, "PUT", {
            quantity: newQty
        });
        await fetchInventory();
    } catch (err) {
        console.error("Failed to adjust quantity:", err);
    }
}

async function deleteItem(itemId) {
    try {
        await apiRequest(`/api/v1/inventory/${itemId}?token=${token}`, "DELETE");
        showToast("Item deleted from inventory", "info");
        await fetchInventory();
    } catch (err) {
        console.error("Failed to delete item:", err);
    }
}

// Manually Add Item Modal
btnAddItemModal.addEventListener("click", () => {
    addItemForm.reset();
    addItemModal.classList.remove("hidden");
});

btnCloseAddItem.addEventListener("click", () => {
    addItemModal.classList.add("hidden");
});

addItemForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("add-name").value.trim();
    const qty = parseFloat(document.getElementById("add-qty").value);
    const unit = document.getElementById("add-unit").value.trim();
    const cat = document.getElementById("add-cat").value;
    const expDays = parseInt(document.getElementById("add-exp-days").value) || 7;

    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + expDays);

    try {
        await apiRequest(`/api/v1/inventory?token=${token}`, "POST", {
            name,
            quantity: qty,
            unit,
            category: cat,
            expires_at: expiresAt.toISOString()
        });
        showToast("Ingredient added!", "success");
        addItemModal.classList.add("hidden");
        await fetchInventory();
    } catch (err) {
        console.error("Failed to add item:", err);
    }
});

// Scan Modal Open/Close handlers
if (btnOpenScan) {
    btnOpenScan.addEventListener("click", (e) => {
        e.preventDefault();
        console.log("Opening scan upload modal...");
        if (scanUploadModal) {
            scanUploadModal.classList.remove("hidden");
        }
    });
}

if (btnCloseScanModal) {
    btnCloseScanModal.addEventListener("click", (e) => {
        e.preventDefault();
        console.log("Closing scan upload modal...");
        if (scanUploadModal) {
            scanUploadModal.classList.add("hidden");
        }
    });
}

// Image Upload / Drag and Drop handlers
if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        const file = e.dataTransfer.files[0];
        if (file) handleImageFile(file);
    });

    dropzone.addEventListener("click", (e) => {
        // Prevent click recursion if clicking children
        if (e.target !== fileUpload && fileUpload) {
            fileUpload.click();
        }
    });
}

if (fileUpload) {
    fileUpload.addEventListener("click", (e) => {
        e.stopPropagation(); // Stop click event bubbling to dropzone
    });

    fileUpload.addEventListener("change", () => {
        const file = fileUpload.files[0];
        if (file) handleImageFile(file);
    });
}

async function handleImageFile(file) {
    if (!file.type.match("image/jpeg") && !file.type.match("image/png")) {
        showToast("Please upload a valid JPEG or PNG image.", "error");
        return;
    }

    // Prepare FormData
    const formData = new FormData();
    formData.append("token", token);
    formData.append("strict_match", toggleStrictMatch.checked);
    formData.append("save_the_food", toggleSaveFood.checked);
    formData.append("image", file);

    // Show loading indicator
    globalLoader.classList.remove("hidden");

    try {
        const response = await fetch("/api/v1/analyze-fridge", {
            method: "POST",
            body: formData
        });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || "Fridge analysis failed.");
        }

        showToast("Fridge analysis completed!", "success");
        
        // Save recipes in UI state and render
        renderRecipes(data.recipes);
        
        // Present discovered ingredients to user for manual validation
        detectedIngredients = data.ingredients;
        showConfirmLoggingModal();
        scanUploadModal.classList.add("hidden");
    } catch (err) {
        console.error("Scan analysis failed:", err);
        showToast(err.message, "error");
    } finally {
        globalLoader.classList.add("hidden");
    }
}

// Manual inventory logging confirmation Modal
function showConfirmLoggingModal() {
    confirmItemsTbody.innerHTML = "";
    
    if (detectedIngredients.length === 0) {
        showToast("AI couldn't detect any ingredients. Try uploading another picture.", "info");
        return;
    }

    detectedIngredients.forEach((item, index) => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-200 py-3 text-xs text-slate-700";
        
        tr.innerHTML = `
            <td class="py-2.5">
                <input type="checkbox" checked class="item-confirm-cb rounded border-slate-300 text-teal-650 focus:ring-teal-500/20" data-idx="${index}">
            </td>
            <td class="py-2.5">
                <input type="text" value="${item.name}" class="item-confirm-name px-2 py-1 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 w-full">
            </td>
            <td class="py-2.5 pr-2">
                <input type="number" step="any" value="${item.quantity}" class="item-confirm-qty px-2 py-1 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 w-full font-mono">
            </td>
            <td class="py-2.5 pr-2">
                <input type="text" value="${item.unit}" class="item-confirm-unit px-2 py-1 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 w-full">
            </td>
            <td class="py-2.5 pr-2">
                <select class="item-confirm-cat px-2 py-1 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 w-full">
                    <option value="Dairy/Eggs" ${item.category === "Dairy/Eggs" || item.category.includes("Dairy") ? "selected" : ""}>Dairy/Eggs</option>
                    <option value="Vegetables" ${item.category === "Vegetables" || item.category.includes("Veg") ? "selected" : ""}>Vegetables</option>
                    <option value="Fruits" ${item.category === "Fruits" || item.category.includes("Fruit") ? "selected" : ""}>Fruits</option>
                    <option value="Proteins" ${item.category === "Proteins" || item.category.includes("Meat") || item.category.includes("Poultry") ? "selected" : ""}>Meat/Proteins</option>
                    <option value="Pantry" ${item.category === "Pantry" ? "selected" : ""}>Pantry</option>
                    <option value="Others" ${!["Dairy/Eggs", "Vegetables", "Fruits", "Proteins", "Pantry"].includes(item.category) ? "selected" : ""}>Others</option>
                </select>
            </td>
            <td class="py-2.5 pr-1">
                <input type="number" min="1" value="${item.days_to_expiration || 7}" class="item-confirm-exp px-2 py-1 bg-slate-50 border border-slate-200 rounded text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 w-full font-mono">
            </td>
        `;
        confirmItemsTbody.appendChild(tr);
    });

    confirmLoggingModal.classList.remove("hidden");
}

btnCancelLogging.addEventListener("click", () => {
    confirmLoggingModal.classList.add("hidden");
    showToast("AI ingredients list discarded.", "info");
});

btnSaveLogging.addEventListener("click", async () => {
    const rows = confirmItemsTbody.querySelectorAll("tr");
    const itemsToSave = [];
    
    rows.forEach(row => {
        const cb = row.querySelector(".item-confirm-cb");
        if (cb && cb.checked) {
            const name = row.querySelector(".item-confirm-name").value.trim();
            const qty = parseFloat(row.querySelector(".item-confirm-qty").value) || 1.0;
            const unit = row.querySelector(".item-confirm-unit").value.trim();
            const category = row.querySelector(".item-confirm-cat").value;
            const expDays = parseInt(row.querySelector(".item-confirm-exp").value) || 7;

            const expiresAt = new Date();
            expiresAt.setDate(expiresAt.getDate() + expDays);

            itemsToSave.push({
                name,
                quantity: qty,
                unit,
                category,
                expires_at: expiresAt.toISOString()
            });
        }
    });

    if (itemsToSave.length === 0) {
        showToast("No ingredients checked to add.", "info");
        confirmLoggingModal.classList.add("hidden");
        return;
    }

    globalLoader.classList.remove("hidden");
    let addedCount = 0;

    try {
        // Save items sequentially
        for (const item of itemsToSave) {
            await apiRequest(`/api/v1/inventory?token=${token}`, "POST", item);
            addedCount++;
        }
        showToast(`Successfully added ${addedCount} ingredients to inventory!`, "success");
        confirmLoggingModal.classList.add("hidden");
        await fetchInventory();
    } catch (err) {
        console.error("Failed to batch save ingredients:", err);
    } finally {
        globalLoader.classList.add("hidden");
    }
});

// Recipe rendering
function renderRecipes(recipes) {
    recipesEmptyState.classList.add("hidden");
    recipesContainer.classList.remove("hidden");
    recipesContainer.innerHTML = "";

    if (!recipes || recipes.length === 0) {
        recipesEmptyState.classList.remove("hidden");
        recipesContainer.classList.add("hidden");
        return;
    }

    recipes.forEach((recipe, idx) => {
        const card = document.createElement("div");
        card.className = "bg-white border border-slate-200/80 rounded-2xl p-4 flex flex-col gap-3 shadow-sm hover:border-teal-200/80 hover:shadow-md transition-all duration-300";
        
        // Create matching ingredients list
        const matchingHtml = recipe.ingredients_used.map(ing => {
            return `<span class="px-2 py-0.5 bg-teal-50 border border-teal-200/50 text-teal-650 rounded text-[9px] font-bold">${ing}</span>`;
        }).join(" ");

        card.innerHTML = `
            <div class="flex items-start justify-between gap-3">
                <h4 class="text-xs font-bold text-slate-800 leading-snug">${recipe.name}</h4>
                <span class="text-[9px] px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-600 font-semibold rounded-full shrink-0 font-mono">${recipe.prep_time}</span>
            </div>
            
            <div class="flex flex-wrap gap-1 mt-1">
                ${matchingHtml}
            </div>

            <!-- Steps trigger -->
            <button class="btn-toggle-steps text-left text-[10px] font-bold text-teal-650 hover:text-teal-700 flex items-center gap-1 cursor-pointer mt-1">
                <span>View Cooking Instructions</span>
                <svg class="w-3.5 h-3.5 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path>
                </svg>
            </button>

            <!-- Steps container (Hidden by default) -->
            <div class="steps-content hidden mt-2 pt-2.5 border-t border-slate-200 text-[10px] text-slate-600 space-y-2 leading-relaxed">
                <ol class="list-decimal list-inside space-y-1.5 pl-1">
                    ${recipe.instructions.map(step => `<li>${step}</li>`).join("")}
                </ol>
            </div>
        `;

        // Instructions expand/collapse toggle
        const toggleBtn = card.querySelector(".btn-toggle-steps");
        const stepsContent = card.querySelector(".steps-content");
        const iconSvg = toggleBtn.querySelector("svg");

        toggleBtn.addEventListener("click", () => {
            const isHidden = stepsContent.classList.contains("hidden");
            if (isHidden) {
                stepsContent.classList.remove("hidden");
                iconSvg.classList.add("rotate-180");
            } else {
                stepsContent.classList.add("hidden");
                iconSvg.classList.remove("rotate-180");
            }
        });

        recipesContainer.appendChild(card);
    });
}

// Initial startup - Check routing and session token
document.addEventListener("DOMContentLoaded", () => {
    // Check if path is a Room link e.g. /room/xyz123
    const path = window.location.pathname;
    const match = path.match(/^\/room\/([^/]+)$/);
    if (match) {
        pendingRoomId = match[1];
        showToast(`Ready to connect room: ${pendingRoomId}. Please sign in.`, "info");
    }

    initDashboard();
});
