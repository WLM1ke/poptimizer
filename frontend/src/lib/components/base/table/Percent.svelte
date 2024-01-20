<script lang="ts">
	export let value: number;
	export let fractionDigits: number | undefined = 1;
</script>

<td class="px-2 text-right">
	{value.toLocaleString(undefined, {
		style: "percent",
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	})}
</td>
