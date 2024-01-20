<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = undefined;
</script>

<td class="px-1 text-right">
	{value.toLocaleString(undefined, {
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
