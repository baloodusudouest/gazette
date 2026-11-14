<script>
  // « À traiter » : une tuile par sorte de geste attendu, avec son nombre ; une tuile ouvre sa liste.
  import { onMount } from 'svelte'
  import UserPlus from '@lucide/svelte/icons/user-plus'
  import BookOpenCheck from '@lucide/svelte/icons/book-open-check'
  import Cake from '@lucide/svelte/icons/cake'
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import FicheForm from '$lib/FicheForm.svelte'
  import { dateCourte, dateLongue } from '$lib/format.js'

  let { onchange, ondeconnecte } = $props()
  let t = $state(null)
  let choisi = $state(null)
  let ficheDe = $state(null)
  let message = $state('')

  async function lire() {
    try {
      t = await api.get('/api/a-traiter')
      if (!choisi) choisi = ['fiches', 'anniversaires', 'relire', 'erreurs'].find((k) => t[k].length) ?? null
      onchange?.()
    } catch (err) {
      if (err.statut === 401) ondeconnecte?.()
      else message = err.message
    }
  }
  async function creer(f) {
    const r = await api.post('/api/personnes', f)
    ficheDe = null
    message = `Fiche créée : le livret de ${f.nom} se prépare.`
    await lire()
    return r
  }
  async function ignorer(sorte, cle) { await api.post('/api/a-traiter/ignorer', { sorte, cle }); await lire() }
  async function ajouter(a, phrase) {
    await api.post(`/api/livrets/${a.id}/mot/ajouter`, { phrase, cle: a.cle })
    message = `Phrase ajoutée au mot des hôtes de ${a.nom}.`
    await lire()
  }
  const tuiles = [
    { cle: 'fiches', nom: 'Invités sans fiche', icone: UserPlus, aide: 'annoncés par Home Assistant' },
    { cle: 'anniversaires', nom: 'Anniversaires proches', icone: Cake, aide: 'à 14 jours du séjour' },
    { cle: 'relire', nom: 'Livrets à relire', icone: BookOpenCheck, aide: 'avant d\'approuver' },
    { cle: 'erreurs', nom: 'Préparations en échec', icone: TriangleAlert, aide: 'sources illisibles' },
  ]
  onMount(lire)
</script>

<header class="mb-5">
  <p class="etiquette">Gazette</p>
  <h1 class="titre">À traiter</h1>
</header>

{#if message}<p class="mb-4 rounded-xl border px-4 py-2 text-sm" role="status">{message}</p>{/if}

{#if t}
  <div class="grid grid-cols-2 gap-3 md:grid-cols-4" role="group" aria-label="Tuiles">
    {#each tuiles as tu}
      {@const Icone = tu.icone}
      {#if t[tu.cle].length}
        <button type="button" aria-pressed={choisi === tu.cle} onclick={() => (choisi = tu.cle)}
                class="flex min-h-28 flex-col gap-1 rounded-2xl border bg-card p-4 text-left transition-colors hover:border-primary aria-pressed:border-primary">
          <span class="flex items-start justify-between"><Icone class="size-6 text-primary" aria-hidden="true" /><span class="chiffre text-3xl">{t[tu.cle].length}</span></span>
          <span class="font-medium">{tu.nom}</span>
          <span class="text-sm text-muted-foreground">{tu.aide}</span>
        </button>
      {/if}
    {/each}
  </div>

  {#if t.total === 0}
    <p class="mt-2 text-sm text-muted-foreground">Rien à traiter. Les livrets des invités attendus sont prêts.</p>
  {/if}

  {#if choisi === 'fiches' && t.fiches.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Invités sans fiche">
      <h2 class="text-lg font-semibold">Invités sans fiche</h2>
      <p class="mt-1 text-sm text-muted-foreground">Le nom vient de la réservation. Crée la fiche avec la date de naissance, ou rattache ce nom à une fiche existante (champ « autres noms » de la fiche).</p>
      <ul class="mt-3 grid gap-3">
        {#each t.fiches as f}
          <li class="rounded-xl border p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span><b>{f.nom}</b> <span class="text-sm text-muted-foreground">· chambre {f.chambre}, {dateCourte(f.du)} → {dateCourte(f.jusqu_au)}</span></span>
              <span class="flex gap-2">
                <Button size="sm" variant="outline" onclick={() => (ficheDe = ficheDe === f.nom ? null : f.nom)}>Créer la fiche</Button>
                <Button size="sm" variant="outline" onclick={() => ignorer('fiche', f.nom)}>Pas de livret</Button>
              </span>
            </div>
            {#if ficheDe === f.nom}<div class="mt-3"><FicheForm valeur={{ nom: f.nom }} onvalider={creer} onannuler={() => (ficheDe = null)} /></div>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'anniversaires' && t.anniversaires.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Anniversaires proches">
      <h2 class="text-lg font-semibold">Anniversaires proches du séjour</h2>
      <ul class="mt-3 grid gap-4">
        {#each t.anniversaires as a}
          <li class="rounded-xl border p-3">
            <p class="flex flex-wrap items-center justify-between gap-2">
              <span><a class="font-semibold underline-offset-4 hover:underline" href={'#/livret/' + a.id}>{a.nom}</a> : anniversaire <b class="text-primary">{a.libelle}</b>,
                le {dateLongue(a.anniversaire)} <span class="text-sm text-muted-foreground">(chambre {a.sejour.chambre}, {dateCourte(a.sejour.du)} → {dateCourte(a.sejour.jusqu_au)})</span></span>
              <Button size="sm" variant="outline" onclick={() => ignorer('anniversaire', a.cle)}>Ignorer</Button>
            </p>
            <ul class="mt-2 grid gap-2">
              {#each a.phrases as p}
                <li class="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span class="font-serif italic">« {p} »</span>
                  <Button size="sm" variant="outline" onclick={() => ajouter(a, p)}>Ajouter au mot des hôtes</Button>
                </li>
              {/each}
            </ul>
          </li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'relire' && t.relire.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Livrets à relire">
      <h2 class="text-lg font-semibold">Livrets à relire</h2>
      <ul class="mt-3 grid gap-2">
        {#each t.relire as r}
          <li class="flex items-center justify-between gap-2"><a class="underline-offset-4 hover:underline" href={'#/livret/' + r.id}>{r.nom}</a>
            {#if r.attendu}<span class="text-xs text-primary">invité attendu</span>{/if}</li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'erreurs' && t.erreurs.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Préparations en échec">
      <h2 class="text-lg font-semibold">Préparations en échec</h2>
      <ul class="mt-3 grid gap-2">
        {#each t.erreurs as r}
          <li><a class="underline-offset-4 hover:underline" href={'#/livret/' + r.id}>{r.nom}</a> <span class="text-sm text-destructive">{r.erreur}</span></li>
        {/each}
      </ul>
    </section>
  {/if}
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
