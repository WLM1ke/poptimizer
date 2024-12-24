<script lang="ts">
	import Add from "$lib/icons/Add.svelte";

	let { onclick }: { onclick: () => void } = $props();
</script>

<td class="flex w-32 justify-center p-2 font-mono">
	<button {onclick} class="hover:text-link-hover">
		<Add />
	</button>
</td>
