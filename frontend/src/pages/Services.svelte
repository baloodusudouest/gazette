<script>
  // « Connexion » : une tuile par service. Gazette lit les sources libres et reçoit les séjours de
  // Home Assistant ; elle n'écrit chez aucun service.
  import { onMount } from 'svelte'
  import BookOpen from '@lucide/svelte/icons/book-open'
  import Globe from '@lucide/svelte/icons/globe'
  import Database from '@lucide/svelte/icons/database'
  import Library from '@lucide/svelte/icons/library'
  import House from '@lucide/svelte/icons/house'
  import FileText from '@lucide/svelte/icons/file-text'
  import BookUser from '@lucide/svelte/icons/book-user'
  import Images from '@lucide/svelte/icons/images'
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import { dateCourte } from '$lib/format.js'

  let { ondeconnecte } = $props()
  let e = $state(null)
  let sonde = $state(null)
  let choisi = $state(null)
  let copie = $state('')            // 0.20.2 : la commande qui vient d'être copiée (Connexion › IA du PC)
  async function copier(texte) {
    try { await navigator.clipboard.writeText(texte); copie = texte }
    catch {           // http sans presse-papiers : on sélectionne la commande, il reste Ctrl+C
      const el = [...document.querySelectorAll('code[data-commande]')].find((c) => c.textContent === texte)
      if (el) { const r = document.createRange(); r.selectNodeContents(el); const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r) }
      copie = ''
    }
    setTimeout(() => { if (copie === texte) copie = '' }, 2000)
  }
  let attente = $state(false)

  async function lire() {
    try { e = await api.get('/api/connexion/etat') } catch (err) { if (err.statut === 401) ondeconnecte?.() }
  }
  async function verifier() {
    attente = true
    try { sonde = await api.post('/api/connexion/verifier') } catch { /* affiché par les voyants */ }
    attente = false
  }
  const services = $derived(e ? [
    { cle: 'wikipedia-fr', nom: 'Wikipédia FR', icone: BookOpen, cache: e.sources.wp, lit: 'pages « mois année », « année en France », « année », « jour mois » (wikitext brut)', ecrit: 'rien' },
    { cle: 'wikipedia-en', nom: 'Wikipédia EN', icone: Globe, cache: null, lit: 'pages « Month Year », en repli quand la semaine est pauvre ; proposées en anglais, jamais choisies seules', ecrit: 'rien' },
    { cle: 'wikidata', nom: 'Wikidata', icone: Database, cache: e.sources.wd, lit: 'notoriété des pages (liens interlangues) et nature « être humain »', ecrit: 'rien' },
    { cle: 'larousse', nom: 'Larousse', icone: Library, cache: e.sources.lar, lit: "Journaux de l'année, chronologie du mois (1966 à 2003). Textes non libres : usage familial, rien ne sort du NAS", ecrit: 'rien' },
    { cle: 'ha', nom: 'Home Assistant', icone: House, cache: null, lit: 'reçoit les séjours sur /ha/sejour (jeton GAZETTE_JETON_HA) ; HA lit /ha/etat', ecrit: 'rien' },
    { cle: 'carnet', nom: 'Carnet', icone: BookUser, cache: null, lit: 'noms et dates de naissance sur /gazette/personnes (jeton commun MAISON_JETON) : fiche créée seule pour un invité connu, saisie assistée, dates comparées', ecrit: 'rien' },
    { cle: 'immich', nom: 'Immich', icone: Images, cache: null, lit: "La Récidive : photos de l'invité entre deux séjours, photos taguées « scandale », aperçus (clé GAZETTE_IMMICH_CLE : asset.read, asset.view, tag.read)", ecrit: 'rien' },
    { cle: 'ia', nom: 'IA du PC', icone: Sparkles, cache: null, lit: `Ollama sur le PC (${e.ia.modele}) : il reçoit des descriptions écrites et les indices de la fiche (jamais une photo, jamais une date de naissance) et rend des propositions (titres de ${e.ia.maxi} caractères au plus, légendes, rumeurs, courrier, horoscope, aides de la Gazette).`, ecrit: 'rien' },
    { cle: 'rendu', nom: 'Rendu PDF', icone: FileText, cache: null, lit: 'Chromium dans le conteneur, polices embarquées', ecrit: 'rien' },
  ] : [])
  function voyant(s) {
    if (s.cle === 'ha') return e.ha.porte ? (e.ha.dernier_appel ? 'ok' : 'attente') : 'ko'
    if (s.cle === 'rendu') return e.rendu.polices && e.rendu_recidive?.polices ? 'ok' : 'ko'
    if (s.cle === 'immich' && !sonde?.immich) return !e.immich.regle ? 'coupe' : e.immich.erreur ? 'ko' : 'attente'
    if (s.cle === 'ia' && !sonde?.ia) return !e.ia.regle ? 'coupe' : e.ia.erreur ? 'ko' : 'attente'
    if (s.cle === 'carnet' && !sonde?.carnet) return !e.carnet.regle ? 'coupe' : e.carnet.erreur ? 'ko' : e.carnet.personnes !== null ? 'ok' : 'attente'
    if (s.cle === 'larousse' && !e.larousse) return 'coupe'
    if (sonde?.[s.cle]) return sonde[s.cle].ok ? 'ok' : sonde[s.cle].ok === null ? 'coupe' : 'ko'
    if (e.erreurs[s.cle]) return 'ko'
    return s.cache ? 'ok' : 'attente'
  }
  function detail(s) {
    if (s.cle === 'ha') return e.ha.porte ? (e.ha.dernier_appel ? `dernier séjour reçu ${dateCourte(e.ha.dernier_appel)}` : 'porte ouverte, rien reçu') : 'porte fermée (jeton absent)'
    if (s.cle === 'rendu') return e.rendu.polices && e.rendu_recidive?.polices ? 'polices présentes' : 'polices absentes'
    if (s.cle === 'immich' && !sonde?.immich) return !e.immich.regle ? 'pas réglé : la Gazette sert à chaque séjour' : e.immich.erreur || 'réglé, pas encore lu'
    if (s.cle === 'ia' && !sonde?.ia) return !e.ia.regle ? 'pas réglée : écris les titres toi-même' : e.ia.erreur || 'réglée, à vérifier (PC allumé ?)'
    if (s.cle === 'carnet' && !sonde?.carnet) return !e.carnet.regle ? 'pas réglé (jeton absent)' : e.carnet.erreur ? e.carnet.erreur
      : e.carnet.personnes !== null ? `${e.carnet.personnes} contacts, ${e.carnet.dates} avec date complète` : 'pas encore lu'
    if (sonde?.[s.cle]) return sonde[s.cle].detail
    if (e.erreurs[s.cle]) return e.erreurs[s.cle]
    return s.cache ? `${s.cache.pages} pages gardées` : 'rien de lu pour l\'instant'
  }
  onMount(lire)
</script>

<header class="mb-5 flex flex-wrap items-end justify-between gap-3">
  <div>
    <p class="etiquette">Gazette</p>
    <h1 class="titre">Connexion</h1>
  </div>
  <Button variant="outline" onclick={verifier} disabled={attente}>{attente ? 'Vérification…' : 'Vérifier les sources'}</Button>
</header>

{#snippet commande(texte)}
  <span class="mt-1 flex items-start gap-2">
    <code data-commande class="min-w-0 flex-1 whitespace-pre-wrap break-all rounded-lg bg-background/70 px-2.5 py-1.5 font-mono text-xs">{texte}</code>
    <button type="button" class="shrink-0 rounded-lg border px-2 py-1 text-xs text-muted-foreground hover:text-foreground" onclick={() => copier(texte)}
            aria-label="Copier la commande">{copie === texte ? 'Copié' : 'Copier'}</button>
  </span>
{/snippet}

{#snippet guideIa(g)}
  {#if e.ia.erreur}<p class="mt-3 rounded-xl border border-destructive/60 px-3 py-2 text-sm" role="alert"><span class="text-muted-foreground">Dernière erreur :</span> {e.ia.erreur}</p>{/if}
  <dl class="mt-4 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
    {#each g.reglages as r}<dt class="text-muted-foreground">{r.nom}</dt><dd class="break-all">{r.valeur}</dd>{/each}
  </dl>

  <h3 class="mt-5 font-semibold">Allumer normalement</h3>
  <ol class="mt-2 grid list-decimal gap-1.5 pl-5 text-sm">
    {#each g.allumer as etape}<li>{etape}</li>{/each}
  </ol>

  <h3 class="mt-5 font-semibold">En cas de problème</h3>
  <p class="text-xs text-muted-foreground">Les commandes se tapent dans PowerShell sur le PC (menu Démarrer › PowerShell).</p>
  <div class="mt-2 grid gap-2">
    {#each g.pannes as p}
      <details class="rounded-xl border px-3 py-2 open:bg-background/40">
        <summary class="cursor-pointer text-sm font-medium">{p.signe}</summary>
        <ul class="mt-2 grid list-disc gap-1 pl-5 text-sm">{#each p.faire as f}<li>{f}</li>{/each}</ul>
        {#each p.commandes as c}{@render commande(c)}{/each}
      </details>
    {/each}
  </div>

  <details class="mt-4 rounded-xl border px-3 py-2">
    <summary class="cursor-pointer text-sm font-medium">Installation (une seule fois, déjà faite)</summary>
    <ol class="mt-2 grid list-decimal gap-2 pl-5 text-sm">
      {#each g.une_fois as u}<li>{u.texte}{#if u.commande}{@render commande(u.commande)}{/if}</li>{/each}
    </ol>
    <p class="mt-2 text-xs text-muted-foreground">Dans la stack : GAZETTE_OLLAMA_URL = adresse du PC et port 11434 ; GAZETTE_OLLAMA_MODELE pour changer de modèle (facultatif).</p>
  </details>
{/snippet}

{#if e}
  <div class="grid grid-cols-2 gap-3 md:grid-cols-3" role="group" aria-label="Services">
    {#each services as s}
      {@const Icone = s.icone}
      {@const v = voyant(s)}
      <button type="button" aria-pressed={choisi === s.cle} onclick={() => (choisi = choisi === s.cle ? null : s.cle)}
              class="flex min-h-28 flex-col gap-1 rounded-2xl border bg-card p-4 text-left transition-colors hover:border-primary aria-pressed:border-primary">
        <span class="flex items-start justify-between">
          <Icone class="size-6 text-primary" aria-hidden="true" />
          <span class="size-2.5 rounded-full {v === 'ok' ? 'bg-valide' : v === 'ko' ? 'bg-destructive' : 'bg-muted-foreground/40'}" aria-label={v}></span>
        </span>
        <span class="font-medium">{s.nom}</span>
        <span class="text-sm text-muted-foreground">{detail(s)}</span>
      </button>
    {/each}
  </div>
  {#each services.filter((s) => s.cle === choisi) as s}
    <section class="mt-4 rounded-2xl border bg-card p-5" aria-label={s.nom}>
      <h2 class="text-lg font-semibold">{s.nom}</h2>
      <p class="mt-2 text-sm"><span class="text-muted-foreground">Lit :</span> {s.lit}</p>
      <p class="text-sm"><span class="text-muted-foreground">Écrit :</span> {s.ecrit}</p>
      {#if s.cle === 'ia' && e.ia.guide}{@render guideIa(e.ia.guide)}{/if}
      {#if s.cle === 'ha' && e.ha.dernier_corps}<p class="mt-2 text-sm text-muted-foreground">Dernier appel : {e.ha.dernier_corps}</p>{/if}
    </section>
  {/each}
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
