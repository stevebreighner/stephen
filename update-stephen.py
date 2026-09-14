from pathlib import Path
import shutil
from datetime import datetime

PROJECT = Path.home() / "Desktop" / "stephen"

SLUG_PAGE = PROJECT / "src/pages/artwork/[slug].astro"
CART_PAGE = PROJECT / "src/pages/cart.astro"

WORKER_URL = "https://stripe-worker.steve-breighner.workers.dev"


# ------------------------------------------------------------
# Checks
# ------------------------------------------------------------

if not PROJECT.exists():
    raise SystemExit(f"Project not found: {PROJECT}")

if not SLUG_PAGE.exists():
    raise SystemExit(f"Slug page not found: {SLUG_PAGE}")


# ------------------------------------------------------------
# Backup existing slug page
# ------------------------------------------------------------

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

backup = SLUG_PAGE.with_name(
    f"[slug].astro.backup-{timestamp}"
)

shutil.copy2(SLUG_PAGE, backup)

print(f"Backed up existing slug page to:")
print(f"  {backup}")


# ------------------------------------------------------------
# New artwork slug page
# ------------------------------------------------------------

slug_page = r'''---
import PageLayout from "../../layouts/PageLayout.astro";

export function getStaticPaths() {
  const artwork = Object.entries(
    import.meta.glob("../../content/artwork/*.md", {
      eager: true,
    })
  );

  return artwork.map(([path, piece]) => ({
    params: {
      slug: path
        .split("/")
        .pop()
        .replace(".md", ""),
    },
    props: {
      piece,
    },
  }));
}

const { piece } = Astro.props;
const slug = Astro.params.slug;
const price = piece.frontmatter.price;
const status = piece.frontmatter.status ?? "Available";
const canBuy = price && status.toLowerCase() !== "sold";
---

<PageLayout title={piece.frontmatter.title}>

<a class="back" href="/artwork">
  ← Back
</a>

<h1>{piece.frontmatter.title}</h1>

<img
  class="hero-image"
  src={piece.frontmatter.image}
  alt={piece.frontmatter.title}
/>

<p>
  <strong>Medium:</strong>
  {piece.frontmatter.medium}
</p>

<p>
  <strong>Size:</strong>
  {piece.frontmatter.size}
</p>

{price && (
  <p>
    <strong>Price:</strong>
    ${price}
  </p>
)}

{canBuy && (
  <button
    class="buy-form"
    id="add-to-cart"
    type="button"
  >
    Add to Cart
  </button>
)}

<script define:vars={{
  slug,
  title: piece.frontmatter.title,
  image: piece.frontmatter.image,
  price
}}>
  const button = document.querySelector("#add-to-cart");

  if (button) {
    button.addEventListener("click", () => {
      const cart = JSON.parse(
        localStorage.getItem("stephen-cart") || "[]"
      );

      cart.push({
        slug,
        title,
        image,
        price: Number.parseFloat(price),
      });

      localStorage.setItem(
        "stephen-cart",
        JSON.stringify(cart)
      );

      window.location.href = "/cart/";
    });
  }
</script>

<div class="content">
  <piece.Content />
</div>

</PageLayout>

<style>
.buy-form {
  appearance: none;
  margin: 1.25rem 0;
  border: 1px solid var(--text);
  background: var(--text);
  color: var(--bg);
  cursor: pointer;
  font: inherit;
  padding: 0.7rem 1rem;
}

.buy-form:hover {
  transform: translateY(-1px);
}

.hero-image {
  width: 100%;
  height: auto;
  max-height: 75vh;
  object-fit: contain;
  display: block;
  margin: 1rem auto;
}

@media (max-width: 768px) {
  .hero-image {
    max-height: 65vh;
  }
}

.content img {
  max-width: 100%;
  height: auto;
  display: block;
}

.page {
  padding: 1rem 1.25rem;
}
</style>
'''

SLUG_PAGE.write_text(slug_page)

print(f"Updated:")
print(f"  {SLUG_PAGE}")


# ------------------------------------------------------------
# Cart page
# ------------------------------------------------------------

cart_page = r'''---
import PageLayout from "../layouts/PageLayout.astro";
---

<PageLayout title="Cart">

  <section class="cart-page">

    <p class="label">YOUR CART</p>

    <h1>Your Cart</h1>

    <div id="cart"></div>

    <div id="empty">
      <p>Your cart is empty.</p>
      <a href="/artwork/">Browse the artwork →</a>
    </div>

    <div id="summary" hidden>

      <div class="total">
        <span>Subtotal</span>
        <span id="subtotal">$0.00</span>
      </div>

      <div class="shipping">
        <span>Shipping</span>
        <span>$4.50</span>
      </div>

      <div class="shipping">
        <span>Tax</span>
        <span id="tax-display">Enter ZIP code</span>
      </div>

      <div class="total grand">
        <strong>Total</strong>
        <strong id="total">$4.50</strong>
      </div>

      <div class="tax-location">
        <label>
          <span>ZIP code</span>
          <input
            id="tax-zip"
            type="text"
            inputmode="numeric"
            maxlength="5"
            autocomplete="postal-code"
            placeholder="ZIP code"
          >
        </label>
      </div>

      <button id="checkout">
        Proceed to Checkout →
      </button>

    </div>

  </section>

</PageLayout>

<script>
  const cartElement = document.querySelector("#cart");
  const emptyElement = document.querySelector("#empty");
  const summaryElement = document.querySelector("#summary");
  const subtotalElement = document.querySelector("#subtotal");
  const totalElement = document.querySelector("#total");
  const taxDisplay = document.querySelector("#tax-display");
  const checkoutButton = document.querySelector("#checkout");
  const taxZip = document.querySelector("#tax-zip");

  let cart = JSON.parse(
    localStorage.getItem("stephen-cart") || "[]"
  );

  let currentTaxRate = 0;

  function render() {
    cartElement.innerHTML = "";

    if (!cart.length) {
      emptyElement.hidden = false;
      summaryElement.hidden = true;
      return;
    }

    emptyElement.hidden = true;
    summaryElement.hidden = false;

    let subtotal = 0;

    cart.forEach((item, index) => {
      const price = Number(item.price) || 0;

      subtotal += price;

      const row = document.createElement("div");
      row.className = "cart-item";

      row.innerHTML = `
        <img
          src="${item.image}"
          alt="${item.title}"
        >

        <div class="info">
          <strong>${item.title}</strong>

          <span>
            $${price.toFixed(2)}
          </span>

          <button
            type="button"
            data-remove="${index}"
          >
            Remove
          </button>
        </div>
      `;

      cartElement.appendChild(row);
    });

    const tax = subtotal * currentTaxRate;
    const total = subtotal + 4.50 + tax;

    subtotalElement.textContent =
      `$${subtotal.toFixed(2)}`;

    if (currentTaxRate > 0) {
      taxDisplay.textContent =
        `$${tax.toFixed(2)}`;
    } else {
      taxDisplay.textContent =
        taxZip.value.trim().length === 5
          ? "$0.00"
          : "Enter ZIP code";
    }

    totalElement.textContent =
      `$${total.toFixed(2)}`;

    cartElement
      .querySelectorAll("[data-remove]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          cart.splice(
            Number(button.dataset.remove),
            1
          );

          localStorage.setItem(
            "stephen-cart",
            JSON.stringify(cart)
          );

          render();
        });
      });
  }

  let taxTimer;

  async function updateTax() {
    const zip = taxZip.value.trim();

    currentTaxRate = 0;

    if (!/^\d{5}$/.test(zip)) {
      taxDisplay.textContent = "Enter ZIP code";
      render();
      return;
    }

    taxDisplay.textContent = "Calculating…";

    clearTimeout(taxTimer);

    taxTimer = setTimeout(async () => {
      try {
        const response = await fetch(
          "https://stripe-worker.steve-breighner.workers.dev/tax-rate?zip=" +
          encodeURIComponent(zip)
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "Unable to determine tax."
          );
        }

        currentTaxRate =
          Number(data.rate) || 0;

        render();

      } catch (error) {
        console.error(
          "TAX LOOKUP ERROR:",
          error
        );

        currentTaxRate = 0;
        taxDisplay.textContent = "ZIP not found";
        render();
      }
    }, 250);
  }

  taxZip.addEventListener(
    "input",
    updateTax
  );

  checkoutButton.addEventListener(
    "click",
    async () => {
      if (!cart.length) {
        alert("Your cart is empty.");
        return;
      }

      const zip = taxZip.value.trim();

      if (!/^\d{5}$/.test(zip)) {
        alert(
          "Please enter your 5-digit ZIP code."
        );
        return;
      }

      checkoutButton.disabled = true;
      checkoutButton.textContent = "Loading…";

      try {
        const response = await fetch(
          "https://stripe-worker.steve-breighner.workers.dev/create-checkout-session",
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              cart: cart.map(
                (item) => item.slug
              ),
              zip,
            }),
          }
        );

        const data = await response.json();

        if (data.url) {
          window.location.href = data.url;
          return;
        }

        throw new Error(
          data.error ||
          "Unable to start checkout."
        );

      } catch (error) {
        console.error(
          "CHECKOUT ERROR:",
          error
        );

        alert(
          "Checkout error: " +
          (error.message || error)
        );

        checkoutButton.disabled = false;
        checkoutButton.textContent =
          "Proceed to Checkout →";
      }
    }
  );

  render();
</script>

<style>
.cart-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 80px 24px 120px;
}

.label {
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  margin-bottom: 18px;
}

h1 {
  font-size: clamp(2.5rem, 6vw, 5rem);
  line-height: 0.95;
  margin: 0 0 55px;
}

.cart-item {
  display: flex;
  gap: 20px;
  padding: 20px 0;
  border-bottom: 1px solid #ddd;
}

.cart-item img {
  width: 100px;
  height: 100px;
  object-fit: cover;
}

.info {
  display: grid;
  align-content: center;
  gap: 7px;
}

.info button {
  width: fit-content;
  padding: 0;
  border: 0;
  background: none;
  text-decoration: underline;
  cursor: pointer;
  font: inherit;
}

#empty {
  line-height: 1.7;
}

#empty a {
  color: inherit;
}

#summary {
  max-width: 500px;
  margin-top: 40px;
}

.total,
.shipping {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}

.grand {
  border-top: 1px solid #ddd;
  margin-top: 10px;
  padding-top: 15px;
  font-size: 1.15rem;
}

.tax-location {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid #ddd;
}

.tax-location label {
  display: grid;
  gap: 7px;
  width: 180px;
  font-size: 0.85rem;
}

.tax-location input {
  box-sizing: border-box;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #bbb;
  border-radius: 3px;
  background: white;
  font: inherit;
}

.tax-location input:focus {
  outline: none;
  border-color: #222;
}

#checkout {
  margin-top: 30px;
  padding: 12px 18px;
  border: 1px solid var(--text);
  background: var(--text);
  color: var(--bg);
  font: inherit;
  cursor: pointer;
}

#checkout:hover {
  transform: translateY(-1px);
}

#checkout:disabled {
  opacity: 0.6;
  cursor: wait;
}

@media (max-width: 600px) {
  .cart-item img {
    width: 80px;
    height: 80px;
  }
}
</style>
'''

CART_PAGE.write_text(cart_page)

print(f"Created:")
print(f"  {CART_PAGE}")

print()
print("Done.")
print()
print("Now run:")
print("  npm run build")
