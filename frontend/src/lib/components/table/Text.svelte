<script lang="ts">
	export let text: string;
	export let center: boolean = false;
</script>

<td class="w-32 p-2 font-mono" class:text-center={center}>
	{text}
</td>
