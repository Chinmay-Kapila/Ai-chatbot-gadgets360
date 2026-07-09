import { ExternalLink, Star, ImageOff } from 'lucide-react'
import { useState } from 'react'

function formatPrice(price, currency = 'INR') {
  if (price === null || price === undefined) return null
  if (currency === 'INR') {
    return `₹${Number(price).toLocaleString('en-IN')}`
  }
  return `${currency} ${Number(price).toLocaleString()}`
}

/**
 * Renders a single product recommendation card: image, title, price,
 * key specs, rating, and a link out to the full Gadgets360 product page.
 */
function ProductCard({ product }) {
  const [imgError, setImgError] = useState(false)
  const specs = Object.entries(product.key_specs || {}).slice(0, 3)
  const price = formatPrice(product.price, product.currency)

  return (
    <div className="flex w-56 shrink-0 flex-col overflow-hidden rounded-xl2 border border-ink-200 bg-white shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md dark:border-ink-700 dark:bg-ink-800">
      <div className="flex h-32 items-center justify-center bg-ink-100 dark:bg-ink-900">
        {product.image_url && !imgError ? (
          <img
            src={product.image_url}
            alt={product.name}
            onError={() => setImgError(true)}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <ImageOff size={22} className="text-ink-300 dark:text-ink-600" />
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3">
        {product.brand && (
          <span className="font-mono text-[0.65rem] uppercase tracking-wide text-brand-500">
            {product.brand}
          </span>
        )}

        <h4 className="line-clamp-2 font-display text-sm font-semibold leading-snug text-ink-900 dark:text-white">
          {product.name}
        </h4>

        <div className="flex items-center gap-2">
          {price && (
            <span className="font-mono text-sm font-semibold text-ink-900 dark:text-white">
              {price}
            </span>
          )}
          {product.rating !== null && product.rating !== undefined && (
            <span className="flex items-center gap-0.5 text-xs text-signal-amber">
              <Star size={12} className="fill-signal-amber text-signal-amber" />
              {product.rating}
            </span>
          )}
        </div>

        {specs.length > 0 && (
          <ul className="mt-0.5 space-y-0.5">
            {specs.map(([key, value]) => (
              <li
                key={key}
                className="truncate text-[0.72rem] text-ink-500 dark:text-ink-400"
              >
                <span className="capitalize text-ink-400 dark:text-ink-500">{key}: </span>
                {String(value)}
              </li>
            ))}
          </ul>
        )}

        {product.url && (
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-auto flex items-center justify-center gap-1 rounded-lg bg-brand-500 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-brand-600"
          >
            View on Gadgets360
            <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  )
}

export default ProductCard
