<script lang="ts">
	let { label, onclick }: { label: string; onclick: () => void } = $props();
</script>

<button
	{onclick}
	type="button"
	class="bg-link-base hover:bg-link-hover my-2 w-32 rounded-lg px-5 py-2.5 font-medium text-white">{label}</button
>
