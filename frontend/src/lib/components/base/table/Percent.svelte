<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = 1;
</script>

<td class="w-28 p-2 text-right font-mono">
	{value.toLocaleString(undefined, {
		style: "percent",
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
