<script>
  // « À traiter » : une tuile par sorte de geste attendu, avec son nombre ; une tuile ouvre sa liste.
  import { onMount } from 'svelte'
  import UserPlus from '@lucide/svelte/icons/user-plus'
  import BookOpenCheck from '@lucide/svelte/icons/book-open-check'
  import Cake from '@lucide/svelte/icons/cake'
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert'
  import CalendarClock from '@lucide/svelte/icons/calendar-clock'
  import Siren from '@lucide/svelte/icons/siren'
  import ImageOff from '@lucide/svelte/icons/image-off'
  import ImagePlus from '@lucide/svelte/icons/image-plus'
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
      if (!choisi) choisi = ['fiches', 'dates', 'anniversaires', 'recidives', 'relire', 'scandales', 'sans_scandale', 'erreurs'].find((k) => t[k]?.length) ?? null
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
  async function depuisCarnet(f) {
    try {
      await api.post('/api/a-traiter/creer-depuis-carnet', { nom: f.nom })
      message = `Fiche créée d'après carnet : le livret de ${f.nom} se prépare.`
      await lire()
    } catch (err) { message = err.message }
  }
  async function prendreDate(d) {
    await api.put(`/api/personnes/${d.id}`, { naissance: d.carnet })
    message = `Date de ${d.nom} corrigée d'après carnet : le livret est refait.`
    await lire()
  }
  const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
  async function ignorer(sorte, cle) { await api.post('/api/a-traiter/ignorer', { sorte, cle }); await lire() }
  async function ajouter(a, phrase) {
    await api.post(`/api/livrets/${a.id}/mot/ajouter`, { phrase, cle: a.cle })
    message = `Phrase ajoutée au mot des hôtes de ${a.nom}.`
    await lire()
  }
  const tuiles = [
    { cle: 'fiches', nom: 'Invités sans fiche', icone: UserPlus, aide: 'annoncés par Home Assistant' },
    { cle: 'dates', nom: 'Dates à vérifier', icone: CalendarClock, aide: 'différentes dans carnet' },
    { cle: 'anniversaires', nom: 'Anniversaires proches', icone: Cake, aide: 'à 14 jours du séjour' },
    { cle: 'recidives', nom: 'Récidives à relire', icone: Siren, aide: 'journal à scandale, dès le 2e séjour' },
    { cle: 'relire', nom: 'Livrets à relire', icone: BookOpenCheck, aide: 'avant d\'approuver' },
    { cle: 'scandales', nom: 'Photos « scandale » à trouver', icone: ImageOff, aide: 'à taguer dans Immich' },
    { cle: 'sans_scandale', nom: 'Aucune photo « scandale »', icone: ImagePlus, aide: 'personne sans photo taguée dans Immich' },
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
  <div class="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4" role="group" aria-label="Tuiles">
    {#each tuiles as tu}
      {@const Icone = tu.icone}
      {#if t[tu.cle]?.length}
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
              <span><b>{f.nom}</b> <span class="text-sm text-muted-foreground">· chambre {f.chambre}, {dateCourte(f.du)} → {dateCourte(f.jusqu_au)}</span>
                {#if f.carnet?.naissance}<span class="block text-sm text-valide">Carnet : né·e le {dateLongue(f.carnet.naissance)}</span>
                {:else if f.carnet?.jour}<span class="block text-sm text-primary">Carnet : le {f.carnet.jour === 1 ? '1er' : f.carnet.jour} {MOIS[f.carnet.mois - 1]}, année inconnue</span>
                {:else if f.carnet?.plusieurs}<span class="block text-sm text-muted-foreground">Carnet : plusieurs contacts à ce nom</span>{/if}</span>
              <span class="flex flex-wrap gap-2">
                {#if f.carnet?.naissance}<Button size="sm" onclick={() => depuisCarnet(f)}>Créer d'après carnet</Button>{/if}
                <Button size="sm" variant="outline" onclick={() => (ficheDe = ficheDe === f.nom ? null : f.nom)}>Créer la fiche</Button>
                <Button size="sm" variant="outline" onclick={() => ignorer('fiche', f.nom)}>Pas de livret</Button>
              </span>
            </div>
            {#if ficheDe === f.nom}<div class="mt-3"><FicheForm valeur={{ nom: f.nom }} onvalider={creer} onannuler={() => (ficheDe = null)} /></div>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'dates' && t.dates.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Dates à vérifier">
      <h2 class="text-lg font-semibold">Dates de naissance à vérifier</h2>
      <p class="mt-1 text-sm text-muted-foreground">Carnet ne donne pas la même date que la fiche. Prendre celle de carnet refait le livret.</p>
      <ul class="mt-3 grid gap-3">
        {#each t.dates as d}
          <li class="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
            <span><a class="font-semibold underline-offset-4 hover:underline" href={'#/livret/' + d.id}>{d.nom}</a>
              <span class="block text-sm">Gazette : {dateLongue(d.gazette)} · <span class="text-primary">carnet : {dateLongue(d.carnet)}</span></span></span>
            <span class="flex flex-wrap gap-2">
              <Button size="sm" onclick={() => prendreDate(d)}>Prendre celle de carnet</Button>
              <Button size="sm" variant="outline" onclick={() => ignorer('date', d.cle)}>Garder la fiche</Button>
            </span>
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
  {:else if choisi === 'recidives' && t.recidives.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Récidives à relire">
      <h2 class="text-lg font-semibold">La Récidive : éditions à relire</h2>
      <p class="mt-1 text-sm text-muted-foreground">Relire chaque photo et sa légende, retirer ce qui pourrait gêner, puis approuver.</p>
      <ul class="mt-3 grid gap-2">
        {#each t.recidives as r}
          <li class="flex items-center justify-between gap-2"><a class="underline-offset-4 hover:underline" href={'#/recidive/' + r.id}>{r.nom} · N° {r.numero}</a>
            <span class="text-xs {r.attendu ? 'text-primary' : 'text-muted-foreground'}">{r.attendu ? 'invité attendu le ' : 'séjour du '}{dateCourte(r.sejour_du)}</span></li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'scandales' && t.scandales.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Photos scandale à trouver">
      <h2 class="text-lg font-semibold">Photos « scandale » à trouver</h2>
      <p class="mt-1 text-sm text-muted-foreground">Pas assez de photos récentes, et aucune photo de la personne avec le tag « scandale » dans Immich pour compléter. Tague quelques vieilles photos dans Immich, puis « Compléter » dans l'édition.</p>
      <ul class="mt-3 grid gap-2">
        {#each t.scandales as s}
          <li class="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
            <span><a class="font-semibold underline-offset-4 hover:underline" href={'#/recidive/' + s.id}>{s.nom}</a>
              <span class="block text-sm text-muted-foreground">{s.photos} photo{s.photos > 1 ? 's' : ''} sur {s.places}{s.tag_absent ? ' · le tag « scandale » n\'existe pas encore dans Immich' : ''}</span></span>
            <Button size="sm" variant="outline" onclick={() => ignorer('scandale', s.cle)}>Ignorer</Button>
          </li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'sans_scandale' && t.sans_scandale?.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Aucune photo scandale">
      <h2 class="text-lg font-semibold">Aucune photo « scandale »</h2>
      <p class="mt-1 text-sm text-muted-foreground">Ces personnes n'ont aucune photo taguée « scandale » dans Immich : La Récidive n'aura rien pour compléter s'il manque des photos récentes. Tague quelques vieilles photos dans Immich ; le compte est refait toutes les 6 heures et envoyé à carnet.</p>
      <ul class="mt-3 grid gap-2">
        {#each t.sans_scandale as s}
          <li class="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3">
            <span><a class="font-semibold underline-offset-4 hover:underline" href={'#/livret/' + s.id}>{s.nom}</a>
              {#if s.tag_absent}<span class="block text-sm text-muted-foreground">le tag « scandale » n'existe pas encore dans Immich</span>{/if}</span>
            <Button size="sm" variant="outline" onclick={() => ignorer('sans_scandale', s.cle)}>Ignorer</Button>
          </li>
        {/each}
      </ul>
    </section>
  {:else if choisi === 'erreurs' && t.erreurs.length}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Préparations en échec">
      <h2 class="text-lg font-semibold">Préparations en échec</h2>
      <ul class="mt-3 grid gap-2">
        {#each t.erreurs as r}
          <li><a class="underline-offset-4 hover:underline" href={r.recidive ? '#/recidive/' + r.recidive : '#/livret/' + r.id}>{r.nom}{r.recidive ? ' · La Récidive' : ''}</a> <span class="text-sm text-destructive">{r.erreur}</span></li>
        {/each}
      </ul>
    </section>
  {/if}
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
