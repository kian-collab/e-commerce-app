/* ─── Config ─────────────────────────────────────────────────────────── */
const API_BASE = '/api';   // proxied by Nginx → Flask

/* ─── State ──────────────────────────────────────────────────────────── */
let products = [];
let cart     = {};   // { productId: { product, qty } }

/* ─── Emoji map (fallback since we have no images yet) ───────────────── */
const EMOJIS = ['📦','🛍','🎁','🖊','📐','🕯','🪴','🧴','🎨','🪞','🧩','⌚'];

/* ─── API helpers ────────────────────────────────────────────────────── */
async function fetchProducts() {
  try {
    const res  = await fetch(`${API_BASE}/products/`);
    if (!res.ok) throw new Error('API error');
    return await res.json();
  } catch {
    return null;
  }
}

async function placeOrder(email, items) {
  const payload = {
    user_email: email,
    items: items.map(({ product, qty }) => ({
      product_id: product.id,
      quantity:   qty,
      unit_price: product.price,
    })),
  };
  const res = await fetch(`${API_BASE}/orders/`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  });
  return res.ok;
}

/* ─── Render products ────────────────────────────────────────────────── */
function renderProducts(list) {
  const grid = document.getElementById('product-grid');
  grid.innerHTML = '';

  if (!list || list.length === 0) {
    grid.innerHTML = '<p style="color:var(--ink-soft);grid-column:1/-1;text-align:center;padding:3rem 0">No products found.</p>';
    return;
  }

  list.forEach((p, i) => {
    const emoji   = EMOJIS[i % EMOJIS.length];
    const inStock = p.stock > 0;
    const card    = document.createElement('div');
    card.className  = 'product-card';
    card.dataset.id = p.id;
    card.style.animationDelay = `${i * 60}ms`;

    card.innerHTML = `
      <div class="product-card__img">
        ${emoji}
        <span class="product-card__badge ${inStock ? '' : 'product-card__badge--out'}">
          ${inStock ? `${p.stock} left` : 'Sold out'}
        </span>
      </div>
      <div class="product-card__body">
        <div class="product-card__name">${escHtml(p.name)}</div>
        <div class="product-card__desc">${escHtml(p.description || 'A well-crafted product.')}</div>
        <div class="product-card__footer">
          <span class="product-card__price">₹${Number(p.price).toFixed(2)}</span>
          <button
            class="product-card__add"
            onclick="addToCart(${p.id})"
            ${inStock ? '' : 'disabled'}
          >${inStock ? 'Add to cart' : 'Out of stock'}</button>
        </div>
      </div>`;
    grid.appendChild(card);
  });
}

/* ─── Filter ─────────────────────────────────────────────────────────── */
function filterProducts(type, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  let filtered = products;
  if (type === 'under50')  filtered = products.filter(p => p.price < 50);
  if (type === 'instock')  filtered = products.filter(p => p.stock > 0);
  renderProducts(filtered);
}

/* ─── Cart ───────────────────────────────────────────────────────────── */
function addToCart(productId) {
  const product = products.find(p => p.id === productId);
  if (!product) return;

  if (cart[productId]) {
    cart[productId].qty++;
  } else {
    cart[productId] = { product, qty: 1 };
  }

  updateCartUI();
  showToast(`${product.name} added to cart`);
  bumpCount();
}

function changeQty(productId, delta) {
  if (!cart[productId]) return;
  cart[productId].qty += delta;
  if (cart[productId].qty <= 0) delete cart[productId];
  updateCartUI();
}

function updateCartUI() {
  const items     = Object.values(cart);
  const totalQty  = items.reduce((s, i) => s + i.qty, 0);
  const totalPrice = items.reduce((s, i) => s + i.qty * i.product.price, 0);

  // Count badge
  document.getElementById('cart-count').textContent = totalQty;

  // Items list
  const container = document.getElementById('cart-items');
  const footer    = document.getElementById('cart-footer');

  if (items.length === 0) {
    container.innerHTML = '<p class="cart-empty">Your cart is empty.</p>';
    footer.style.display = 'none';
    return;
  }

  footer.style.display = 'flex';
  document.getElementById('cart-total').textContent = `₹${totalPrice.toFixed(2)}`;

  container.innerHTML = '';
  items.forEach(({ product, qty }, i) => {
    const emoji = EMOJIS[products.indexOf(product) % EMOJIS.length];
    const el    = document.createElement('div');
    el.className = 'cart-item';
    el.style.animationDelay = `${i * 40}ms`;
    el.innerHTML = `
      <div class="cart-item__emoji">${emoji}</div>
      <div class="cart-item__info">
        <div class="cart-item__name">${escHtml(product.name)}</div>
        <div class="cart-item__price">₹${Number(product.price).toFixed(2)} each</div>
      </div>
      <div class="cart-item__qty">
        <button onclick="changeQty(${product.id}, -1)">−</button>
        <span>${qty}</span>
        <button onclick="changeQty(${product.id}, +1)">+</button>
      </div>`;
    container.appendChild(el);
  });
}

function toggleCart() {
  document.getElementById('cart-drawer').classList.toggle('open');
  document.getElementById('cart-overlay').classList.toggle('open');
}

/* ─── Checkout ───────────────────────────────────────────────────────── */
async function checkout() {
  const items = Object.values(cart);
  if (items.length === 0) return;

  const email = prompt('Enter your email to place the order:');
  if (!email || !email.includes('@')) {
    showToast('Please enter a valid email');
    return;
  }

  const ok = await placeOrder(email, items);
  if (ok) {
    cart = {};
    updateCartUI();
    toggleCart();
    showToast('Order placed! Thank you.');
  } else {
    showToast('Could not place order — API unavailable');
  }
}

/* ─── Utilities ──────────────────────────────────────────────────────── */
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

function bumpCount() {
  const el = document.getElementById('cart-count');
  el.classList.remove('bump');
  void el.offsetWidth;
  el.classList.add('bump');
  setTimeout(() => el.classList.remove('bump'), 300);
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

/* ─── Boot ───────────────────────────────────────────────────────────── */
async function init() {
  const data = await fetchProducts();

  if (!data) {
    // Show mock data so the UI is useful even without a running API
    products = [
      { id:1, name:'Ceramic mug',       description:'Hand-thrown, food-safe glaze.',       price:24.99, stock:12 },
      { id:2, name:'Linen notebook',    description:'180 gsm cream pages, lay-flat spine.', price:18.50, stock: 5 },
      { id:3, name:'Brass bookmark',    description:'Solid brass, aged finish.',             price: 9.00, stock: 0 },
      { id:4, name:'Beeswax candle',    description:'40-hour burn, cotton wick.',            price:14.00, stock:20 },
      { id:5, name:'Walnut pen tray',   description:'Oiled walnut, magnetic catch.',         price:32.00, stock: 8 },
      { id:6, name:'Cotton tote',       description:'12 oz canvas, inside pocket.',          price:22.00, stock: 3 },
    ];
    document.getElementById('error-msg').style.display = 'block';
    document.getElementById('error-msg').textContent =
      'Flask API not reachable — showing demo products.';
  } else {
    products = data;
  }

  renderProducts(products);
}

init();
