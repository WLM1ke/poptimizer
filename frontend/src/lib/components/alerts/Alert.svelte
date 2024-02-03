<script lang="ts">
	import InfoIcon from "$lib/icons/InfoIcon.svelte";

	export let info: boolean;
	export let msg: string;
</script>

<div
	class="m-2 flex items-center gap-1 rounded-lg border p-2"
	class:bg-bg-info={info}
	class:border-bdr-info={info}
	class:text-text-info={info}
	class:bg-bg-alert={!info}
	class:border-bdr-alert={!info}
	class:text-text-alert={!info}
	role="alert"
>
	<InfoIcon />
	<span class="text-sm">{msg}</span>
</div>
