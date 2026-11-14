<script>
  import { ETATS } from '$lib/format.js'
  let { etat } = $props()
  const e = $derived(ETATS[etat] ?? { nom: etat, ton: 'muted' })
</script>

<span class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium
             {e.ton === 'primary' ? 'border-primary/60 text-primary' : e.ton === 'valide' ? 'border-valide/60 text-valide' : 'text-muted-foreground'}">
  <span class="size-1.5 rounded-full {e.ton === 'primary' ? 'bg-primary' : e.ton === 'valide' ? 'bg-valide' : 'bg-muted-foreground/60'}
               {etat === 'en_preparation' ? 'animate-pulse' : ''}" aria-hidden="true"></span>
  {e.nom}
</span>
