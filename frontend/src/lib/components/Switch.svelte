<script lang="ts">
	let { label, checked, onchange }: { label: string; checked: boolean; onchange: () => void } = $props();
</script>

<label class="relative inline-flex cursor-pointer items-center">
	<input type="checkbox" class="peer sr-only" bind:checked {onchange} />
	<div
		class="bg-bg-accent peer-checked:bg-link-base peer h-6 w-11 rounded-full after:absolute after:start-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-full"
	></div>
	<span class="text-text-main ms-3">{label}</span>
</label>
