<script>
  // 0.20 : les anciens numéros — chaque Gazette et chaque Récidive approuvée dont le séjour est fini — rangés par
  // année, avec la lecture, les PDF et la réimpression. Ils quittent la liste Livrets.
  import { onMount } from 'svelte'
  import Download from '@lucide/svelte/icons/download'
  import { api } from '$lib/api.js'
  import { dateCourte } from '$lib/format.js'

  let { ondeconnecte } = $props()
  let liste = $state(null)
  let erreur = $state('')
  let cherche = $state('')
  let annee = $state('')
  let journal = $state('')

  onMount(async () => {
    try { liste = (await api.get('/api/archives')).archives }
    catch (err) { if (err.statut === 401) ondeconnecte?.(); else erreur = err.message }
  })
  const plat = (t) => (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  const annees = $derived([...new Set((liste ?? []).map((a) => a.sejour.du.slice(0, 4)))])
  const vues = $derived((liste ?? []).filter((a) => (!cherche || plat(a.nom).includes(plat(cherche)))
    && (!annee || a.sejour.du.startsWith(annee)) && (!journal || a.journal === journal)))
  const parAnnee = $derived(Object.entries(vues.reduce((m, a) => ((m[a.sejour.du.slice(0, 4)] ??= []).push(a), m), {})))
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">Archives</h1>
  <p class="mt-1 text-sm text-muted-foreground">Les numéros approuvés dont le séjour est fini : Gazette du premier séjour, chaque Récidive, et chaque édition spéciale Eurovision.</p>
</header>

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#if liste}
  <div class="mb-5 flex flex-wrap items-center gap-2">
    <input class="h-10 min-w-0 flex-1 rounded-lg border bg-background px-3 text-sm sm:max-w-xs" placeholder="Chercher un nom…" bind:value={cherche} aria-label="Chercher un nom" />
    <select class="h-10 rounded-lg border bg-background px-2 text-sm" bind:value={annee} aria-label="Année">
      <option value="">Toutes les années</option>
      {#each annees as a}<option value={a}>{a}</option>{/each}
    </select>
    <select class="h-10 rounded-lg border bg-background px-2 text-sm" bind:value={journal} aria-label="Journal">
      <option value="">Tous les journaux</option><option value="gazette">La Gazette</option><option value="recidive">La Récidive</option><option value="eurovision">Édition Eurovision</option>
    </select>
  </div>
  {#if !liste.length}
    <p class="text-sm text-muted-foreground">Rien d'archivé pour l'instant : un numéro approuvé arrive ici le lendemain de la fin du séjour.</p>
  {:else if !vues.length}
    <p class="text-sm text-muted-foreground">Aucun numéro pour cette recherche.</p>
  {/if}
  {#each parAnnee as [an, items]}
    <section class="mb-6" aria-label="Archives {an}">
      <h2 class="etiquette mb-3">{an}</h2>
      <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Numéros de {an}">
        {#each items as a (a.journal + a.id)}
          <li class="flex h-full flex-col gap-2 rounded-2xl border bg-card p-4">
            <a href={a.lien} class="flex flex-col gap-1 hover:text-primary">
              <span class="flex items-start justify-between gap-2">
                <span class="font-medium">{a.nom}</span>
                <span class="shrink-0 rounded-full border px-2 py-0.5 text-[0.7rem] {a.journal === 'recidive' ? 'border-destructive/60 text-destructive' : a.journal === 'eurovision' ? 'border-valide/60 text-valide' : 'border-primary/60 text-primary'}">
                  {a.journal === 'recidive' ? `La Récidive · N° ${a.numero}` : a.journal === 'eurovision' ? 'Édition Eurovision' : 'La Gazette'}</span>
              </span>
              <span class="text-sm text-muted-foreground">{a.journal === 'eurovision' ? `soirée du ${dateCourte(a.sejour.du)} · N° ${a.numero}` : `séjour du ${dateCourte(a.sejour.du)} au ${dateCourte(a.sejour.jusqu_au)}`}{a.sejour.chambre ? ` · chambre ${a.sejour.chambre}` : ''}</span>
              {#if a.titre}<span class="line-clamp-2 font-serif text-sm italic">« {a.titre} »</span>{/if}
            </a>
            <span class="mt-auto flex flex-wrap gap-3 text-xs">
              <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`${a.pdf}?mode=impose`}><Download class="size-3.5" aria-hidden="true" />PDF à imprimer</a>
              <a class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={`${a.pdf}?mode=lecture`}><Download class="size-3.5" aria-hidden="true" />PDF lecture</a>
            </span>
          </li>
        {/each}
      </ul>
    </section>
  {/each}
{:else if !erreur}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
