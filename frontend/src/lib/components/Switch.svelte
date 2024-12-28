<script lang="ts">
	let { label, checked, onchange }: { label: string; checked: boolean; onchange: () => void } = $props();
</script>

<label class="relative inline-flex cursor-pointer items-center">
	<input type="checkbox" class="peer sr-only" bind:checked {onchange} />
	<div
		class="peer h-6 w-11 rounded-full bg-bg-accent after:absolute after:start-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-link-base peer-checked:after:translate-x-full"
	></div>
	<span class="ms-3 text-text-main">{label}</span>
</label>
