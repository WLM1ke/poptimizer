<script lang="ts">
	let { label, onclick }: { label: string; onclick: () => void } = $props();
</script>

<button
	{onclick}
	type="button"
	class="my-2 w-32 rounded-lg bg-link-base px-5 py-2.5 font-medium text-white hover:bg-link-hover">{label}</button
>
