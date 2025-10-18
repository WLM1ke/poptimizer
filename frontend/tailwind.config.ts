import { fontFamily } from "tailwindcss/defaultTheme";

/** @type {import('tailwindcss').Config} */
export default {
	content: ["./src/**/*.{html,js,svelte,ts}"],
	theme: {
		extend: {
			colors: {
				link: {
					base: "rgb(var(--link))",
					hover: "rgb(var(--link-hover))"
				},
				text: {
					main: "rgb(var(--text-main))",
					muted: "rgb(var(--text-muted))",
					info: "rgb(var(--text-info))",
					alert: "rgb(var(--text-alert))"
				},
				bg: {
					main: "rgb(var(--bg-main))",
					medium: "rgb(var(--bg-medium))",
					accent: "rgb(var(--bg-accent))",
					sidebar: "rgb(var(--bg-sidebar))",
					info: "rgb(var(--bg-info))",
					alert: "rgb(var(--bg-alert))"
				},
				bdr: {
					info: "rgb(var(--bdr-info))",
					alert: "rgb(var(--bdr-alert))"
				}
			},
			gridTemplateColumns: {
				layout: "max-content auto"
			},
			gridTemplateRows: {
				layout: "min-content auto"
			},
			fontFamily: {
				logo: ["Roboto Condensed", ...fontFamily.sans]
			}
		}
	},
	plugins: []
};
