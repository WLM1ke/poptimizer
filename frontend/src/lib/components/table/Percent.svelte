<script lang="ts">
	import { formatPercent } from "$lib/format";

	let { value, fractionDigits = 1 }: { value: number; fractionDigits?: number | undefined } = $props();
</script>

<td class="w-32 p-2 text-right font-mono">
	{formatPercent(value, fractionDigits)}
</td>
