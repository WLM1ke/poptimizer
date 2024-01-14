import defaultTheme from "tailwindcss/defaultTheme";

/** @type {import('tailwindcss').Config} */
export default {
	content: ["./src/**/*.{html,js,svelte,ts}"],
	theme: {
		extend: {
			colors: {
				link: "rgb(var(--link) / <alpha-value>)",
				text: {
					main: "rgb(var(--text-main) / <alpha-value>)",
					muted: "rgb(var(--text-muted) / <alpha-value>)",
					info: "rgb(var(--text-info) / <alpha-value>)",
					alert: "rgb(var(--text-alert) / <alpha-value>)"
				},
				bg: {
					main: "rgb(var(--bg-main) / <alpha-value>)",
					medium: "rgb(var(--bg-medium) / <alpha-value>)",
					accent: "rgb(var(--bg-accent) / <alpha-value>)",
					sidebar: "rgb(var(--bg-sidebar) / <alpha-value>)",
					info: "rgb(var(--bg-info) / <alpha-value>)",
					alert: "rgb(var(--bg-alert) / <alpha-value>)"
				},
				bdr: {
					info: "rgb(var(--bdr-info) / <alpha-value>)",
					alert: "rgb(var(--bdr-alert) / <alpha-value>)"
				}
			},
			gridTemplateColumns: {
				layout: "max-content auto"
			},
			gridTemplateRows: {
				layout: "min-content auto"
			},
			fontFamily: {
				logo: ["Roboto Condensed", ...defaultTheme.fontFamily.sans]
			}
		}
	},
	plugins: []
};
