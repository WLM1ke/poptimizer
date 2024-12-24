<script lang="ts">
	import Delete from "$lib/icons/Delete.svelte";

	let { onclick }: { onclick: () => void } = $props();
</script>

<td class="flex w-32 justify-center p-2 font-mono">
	<button {onclick} class="hover:text-link-hover">
		<Delete />
	</button>
</td>
