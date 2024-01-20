<script lang="ts">
	export let label: string;
	export let checked: boolean;
</script>

<label class="relative inline-flex cursor-pointer items-center">
	<input type="checkbox" class="peer sr-only" bind:value={checked} bind:checked on:change />
	<div
		class="peer h-6 w-11 rounded-full bg-bg-accent after:absolute after:start-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-link peer-checked:after:translate-x-full"
	></div>
	<span class="ms-3 text-text-main">{label}</span>
</label>
