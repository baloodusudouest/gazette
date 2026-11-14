<script>
  // « Réglages » : ce qui vient de la stack (affiché), le journal, la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  let { session, deconnecter } = $props()
  let r = $state(null)
  const GESTES = { preparation: 'livret préparé', approuver: 'livret approuvé', fiche: 'fiche', erreur: 'échec de préparation' }
  onMount(async () => { try { r = await api.get('/api/reglages') } catch { /* déconnecté */ } })
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Réglages</h1>
</header>

{#if r}
  <section class="rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Le journal</h2>
    <p class="mt-1 text-sm text-muted-foreground">Réglés dans la stack (variables GAZETTE_TITRE, GAZETTE_SIGNATURE, GAZETTE_LIEU).</p>
    <dl class="mt-3 grid grid-cols-[8rem_1fr] gap-y-1 text-sm">
      <dt class="text-muted-foreground">Titre</dt><dd class="font-serif">{r.titre}</dd>
      <dt class="text-muted-foreground">Signature</dt><dd class="font-serif italic">{r.signature}</dd>
      <dt class="text-muted-foreground">Lieu</dt><dd>{r.lieu}</dd>
      <dt class="text-muted-foreground">Larousse</dt><dd>{r.larousse ? 'utilisé (1966-2003)' : 'coupé (GAZETTE_LAROUSSE=non)'}</dd>
      <dt class="text-muted-foreground">Impression</dt><dd>{r.lecture_seule ? 'lecture seule : rien ne part à l\'imprimante' : 'à venir (temps 3) : PDF à imprimer pour l\'instant'}</dd>
    </dl>
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Règles</h2>
    <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
      <li>La une : le jour même, sinon la veille, la semaine, le mois — la portée est écrite au-dessus du titre.</li>
      <li>Drames (décès, attentats, catastrophes…) : jamais choisis seuls, sur aucun bloc ; visibles à la relecture avec leur raison.</li>
      <li>Textes en anglais : proposés en repli, jamais choisis seuls.</li>
      <li>L'année est toujours affichée ; l'âge en chiffres, jamais.</li>
      <li>Anniversaire à 14 jours ou moins du séjour : phrases proposées dans À traiter.</li>
    </ul>
  </section>

  <section class="mt-4 rounded-2xl border bg-card p-5">
    <h2 class="text-lg font-semibold">Journal</h2>
    {#if r.journal.length === 0}
      <p class="mt-1 text-sm text-muted-foreground">Rien pour l'instant.</p>
    {:else}
      <ul class="mt-2 grid gap-1 text-sm">
        {#each r.journal as j}
          <li class="flex gap-3"><span class="w-36 shrink-0 text-muted-foreground">{j.le.replace('T', ' ').slice(0, 16)}</span>
            <span>{GESTES[j.geste] ?? j.geste}{j.nom ? ' · ' + j.nom : ''}{j.detail ? ' · ' + j.detail : ''}</span></li>
        {/each}
      </ul>
    {/if}
  </section>
{/if}

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Gazette {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
