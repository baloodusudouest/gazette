<script>
  // 0.22 : sous une série de propositions de l'IA du PC : le modèle utilisé (discret) et « Autres propositions
  // (qwen) », qui refait la même demande avec le second modèle (Réglages › Second modèle de l'IA). Les nouvelles
  // propositions remplacent les anciennes, comme une nouvelle demande. Bouton absent si le réglage est vide.
  import { nomCourt } from '$lib/format.js'
  let { modele = '', second = '', attente = false, onautres } = $props()
</script>

{#if modele || second}
  <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-2 text-[0.7rem] text-muted-foreground">
    <span>{modele ? `Modèle : ${modele}` : ''}</span>
    {#if second}
      <button type="button" class="hover:text-foreground disabled:opacity-50" disabled={attente} onclick={() => onautres?.()}
              title="Refait la même demande avec {second}">{attente ? '…' : `Autres propositions (${nomCourt(second)})`}</button>
    {/if}
  </div>
{/if}
