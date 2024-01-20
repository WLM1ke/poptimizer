<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = undefined;
</script>

<td class="w-28 p-2 text-right font-mono">
	{value.toLocaleString(undefined, {
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
