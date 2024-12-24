<script lang="ts">
	import type { Snippet } from "svelte";

	let { headers, rows }: { headers: string[]; rows: Snippet } = $props();
</script>

<table class="mt-2">
	<thead>
		<tr>
			{#each headers as text}
				<th class="p-2">
					{text}
				</th>
			{/each}
		</tr>
	</thead>
	<tbody>
		{@render rows()}
	</tbody>
</table>
