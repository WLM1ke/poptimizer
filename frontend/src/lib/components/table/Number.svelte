<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = undefined;
</script>

<td class="w-32 p-2 text-right font-mono">
	{value.toLocaleString("RU", {
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
