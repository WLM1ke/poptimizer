<script lang="ts">
	import InfoIcon from "$lib/icons/InfoIcon.svelte";

	export let info = false;
</script>

<div
	class="flex items-center gap-1 rounded-lg border p-2"
	class:bg-bg-info={info}
	class:border-bdr-info={info}
	class:text-text-info={info}
	class:bg-bg-alert={!info}
	class:border-bdr-alert={!info}
	class:text-text-alert={!info}
	role="alert"
>
	<InfoIcon />
	<span class="text-sm"> Info alert! Change a few things up and try submitting again. </span>
</div>
