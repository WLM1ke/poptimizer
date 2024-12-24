<script lang="ts">
	import { formatNumber } from "$lib/format";

	let { value, fractionDigits = undefined }: { value: number; fractionDigits?: number | undefined } = $props();
</script>

<td class="w-32 p-2 text-right font-mono">
	{formatNumber(value, fractionDigits)}
</td>
