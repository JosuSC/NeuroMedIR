/** @type {import('tailwindcss').Config} */
export default {
    darkMode: "class",
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                "on-primary-fixed-variant": "#004491",
                "on-secondary": "#ffffff",
                "on-secondary-fixed-variant": "#3b4951",
                "tertiary": "#3e4246",
                "primary-fixed-dim": "#acc7ff",
                "outline-variant": "#c2c6d4",
                "tertiary-fixed-dim": "#c3c7cc",
                "inverse-primary": "#acc7ff",
                "primary-fixed": "#d7e2ff",
                "inverse-surface": "#2e3132",
                "secondary-container": "#d3e2ed",
                "surface-dim": "#d9dadb",
                "outline": "#727784",
                "tertiary-fixed": "#e0e3e8",
                "surface-variant": "#e1e3e4",
                "on-secondary-container": "#56656e",
                "secondary": "#526069",
                "secondary-fixed": "#d6e5ef",
                "on-background": "#191c1d",
                "surface-container-high": "#e7e8e9",
                "on-tertiary-fixed": "#181c20",
                "on-secondary-fixed": "#0f1d25",
                "inverse-on-surface": "#f0f1f2",
                "on-primary-container": "#bbd0ff",
                "on-primary-fixed": "#001a40",
                "background": "#f8f9fa",
                "on-primary": "#ffffff",
                "primary": "#003f87",
                "surface-bright": "#f8f9fa",
                "on-surface-variant": "#424752",
                "secondary-fixed-dim": "#bac9d3",
                "surface-container-highest": "#e1e3e4",
                "surface-container-low": "#f3f4f5",
                "on-tertiary-fixed-variant": "#43474c",
                "surface": "#f8f9fa",
                "on-tertiary": "#ffffff",
                "on-error-container": "#93000a",
                "surface-tint": "#115cb9",
                "surface-container-lowest": "#ffffff",
                "primary-container": "#0056b3",
                "on-error": "#ffffff",
                "error-container": "#ffdad6",
                "on-tertiary-container": "#cdd0d5",
                "tertiary-container": "#55595e",
                "on-surface": "#191c1d",
                "error": "#ba1a1a",
                "surface-container": "#edeeef"
            },
            borderRadius: {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "9999px"
            },
            spacing: {
                "md": "1rem",
                "gutter": "1.5rem",
                "lg": "1.5rem",
                "xs": "0.25rem",
                "sm": "0.5rem",
                "xl": "2rem",
                "unit": "4px",
                "margin": "2rem"
            },
            fontFamily: {
                "data-tabular": ["Inter"],
                "body-md": ["Inter"],
                "label-caps": ["Inter"],
                "body-lg": ["Inter"],
                "h2": ["Inter"],
                "body-sm": ["Inter"],
                "h3": ["Inter"],
                "h1": ["Inter"]
            },
            fontSize: {
                "data-tabular": ["0.875rem", { "lineHeight": "1.4", "letterSpacing": "0", "fontWeight": "500" }],
                "body-md": ["1rem", { "lineHeight": "1.5", "letterSpacing": "0", "fontWeight": "400" }],
                "label-caps": ["0.75rem", { "lineHeight": "1", "letterSpacing": "0.05em", "fontWeight": "700" }],
                "body-lg": ["1.125rem", { "lineHeight": "1.6", "letterSpacing": "0", "fontWeight": "400" }],
                "h2": ["2rem", { "lineHeight": "1.25", "letterSpacing": "-0.01em", "fontWeight": "600" }],
                "body-sm": ["0.875rem", { "lineHeight": "1.5", "letterSpacing": "0", "fontWeight": "400" }],
                "h3": ["1.5rem", { "lineHeight": "1.3", "letterSpacing": "0", "fontWeight": "600" }],
                "h1": ["2.5rem", { "lineHeight": "1.2", "letterSpacing": "-0.02em", "fontWeight": "700" }]
            }
        }
    }
}