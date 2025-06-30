module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/js/**/*.js"
    ],
    theme: {
        extend: {
            animation: {
                'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
            }
        }
    },
    plugins: [require("daisyui")],
    daisyui: {
        themes: [{
            "scandy": {
                "primary": "#374151",      // Dunkelgrau statt Orange
                "primary-content": "#ffffff",
                "secondary": "#6b7280",    // Mittleres Grau
                "secondary-content": "#ffffff",
                "accent": "#ff6600",       // Orange nur für Akzente
                "accent-content": "#ffffff",
                "neutral": "#1f2937",      // Dunkelgrau/Schwarz
                "neutral-content": "#ffffff",
                "base-100": "#ffffff",     // Weiß
                "base-200": "#f9fafb",     // Sehr helles Grau
                "base-300": "#f3f4f6",     // Hellgrau
                "base-content": "#374151", // Dunkelgrau für Text
                "info": "#3abff8",
                "success": "#36d399",
                "warning": "#fbbd23",
                "error": "#f87272",
            }
        }],
    }
} 