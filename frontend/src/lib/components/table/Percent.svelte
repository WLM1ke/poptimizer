<script lang="ts">
	let { value, fractionDigits = 1 }: { value: number; fractionDigits?: number | undefined } = $props();
</script>

<td class="w-32 p-2 text-right font-mono">
	{value.toLocaleString("RU", {
		style: "percent",
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
