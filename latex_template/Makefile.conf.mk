NUMJOBS = $(shell getconf _NPROCESSORS_ONLN)
# uncomment to parallel builds by default
# or set MAKEFLAGS="-j$(getconf _NPROCESSORS_ONLN)" in your shell rc
#MAKEFLAGS += --jobs=$(NUMJOBS)

# define SKIP if certain *.tex or *.tikz files are not to be build directly
# but reside in the root or a figures dir
# e.g. if they are only to be included in other documents or
# are utterly broken and should not be build
SKIP :=

PDFLATEX_FLAGS := -shell-escape
BIBTEX_FLAGS :=
TEXINPUTS := $(CURDIR):$(CURDIR)/tumcommon:$(CURDIR)/tumexam:

.DEFAULT_GOAL := exam


# ------------
# Exam targets
# ------------

EXAM := exam
EXAMSRC := $(EXAM:=.tex)
EXAMPDF := $(EXAMSRC:.tex=.pdf)

exam: ## exam (default)

EXAMSOLUTIONPDF := $(EXAMPDF:.pdf=-solution.pdf)
SPECIALTEXPDF += $(EXAMSOLUTIONPDF)
$(EXAMSOLUTIONPDF): $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,solution)
.PHONY: solution
solution: $(EXAMSOLUTIONPDF) ## exam with sample solution

EXAMCORRECTIONPDF := $(EXAMPDF:.pdf=-correction.pdf)
SPECIALTEXPDF += $(EXAMCORRECTIONPDF)
$(EXAMCORRECTIONPDF): $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,correction)
.PHONY: correction
correction: $(EXAMCORRECTIONPDF:.pdf=-book.pdf) ## exam with correction notes
SMALLBOOKSRC += $(EXAMCORRECTIONPDF)

EXAMEXAMPLEPDF := $(EXAMPDF:.pdf=-example.pdf)
SPECIALTEXPDF += $(EXAMEXAMPLEPDF)
$(EXAMEXAMPLEPDF): $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,example)
.PHONY: example
example: $(EXAMEXAMPLEPDF:.pdf=-book.pdf) ## example exam (how it is printed)
BOOKSRC += $(EXAMEXAMPLEPDF)

EXAMHUDPDF := hud.pdf
$(EXAMHUDPDF): $(EXAMPDF) $(EXAMCORRECTIONPDF)
	$(if $(PDFTKAVAILABLE), pdftk A=$< B=$(word 2,$^) shuffle A B output -, qpdf $< --collate --pages $< $(word 2,$^) -- -) | pdfjam --nup 2x1 --landscape --a4paper --frame true --outfile $@ 2>/dev/null
.PHONY: hud
hud: $(EXAMHUDPDF) ## exam and correction side by side

.PHONY: all
all: ## exam, solution, correction, example and hud
ALLTARGET += exam solution correction example hud


# --------------
# Examid targets
# --------------

EXAMOUT := exam-out
SOLUTIONOUT := solution-out
EXAMIDS := $(shell seq -f "%04.0f" 9999)

EXAMIDPDF := $(EXAMIDS:%=$(EXAMOUT)/E%.pdf)
SPECIALTEXPDF += $(EXAMIDPDF)
EXAMIDSTEM := $(EXAMIDPDF:$(EXAMOUT)/E%.pdf=E%)

SOLUTIONIDPDF := $(EXAMIDS:%=$(SOLUTIONOUT)/E%-solution.pdf)
SPECIALTEXPDF += $(SOLUTIONIDPDF)
SOLUTIONIDSTEM := $(SOLUTIONIDPDF:$(SOLUTIONOUT)/E%-solution.pdf=E%-solution)

$(EXAMIDPDF): $(EXAMOUT)/E%.pdf: $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,$(EXAM)_$*)
	cp $(BUILDDIR)/$(EXAMSRC)/$(EXAM)_$*/$(EXAM)_$*-pages.csv $(EXAMOUT)/E$*-pages.csv
	cp $(BUILDDIR)/$(EXAMSRC)/$(EXAM)_$*/$(EXAM)_$*-boxes.csv $(EXAMOUT)/E$*-boxes.csv
	cp $(BUILDDIR)/$(EXAMSRC)/$(EXAM)_$*/$(EXAM)_$*-pagecodes.csv $(EXAMOUT)/E$*-pagecodes.csv
.PHONY: $(EXAMIDSTEM)

$(EXAMIDSTEM): E%: $(EXAMOUT)/E%-book.pdf
BOOKSRC += $(EXAMIDPDF)

$(SOLUTIONIDPDF): $(SOLUTIONOUT)/E%-solution.pdf: $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,solution_$*)

.PHONY: $(SOLUTIONIDSTEM)
$(SOLUTIONIDSTEM): E%: $(SOLUTIONOUT)/E%.pdf

#FIXME: EXAMCOUNT=N examids builds 1..N and 5001..5000+N, also works for N=0. What does not work is when bulding a single exam `make E0001` that E5001 is also (re)built.
ifeq ($(EXAMCOUNTSTART),)
EXAMCOUNTSTART := 1
endif
ifeq ($(EXAMCOUNT),)
EXAMCOUNT := 0
EXAMIDLIST :=
else
EXAMIDLIST := $(shell seq -f "%04.0f" $(EXAMCOUNTSTART) $$(($(EXAMCOUNTSTART)+$(EXAMCOUNT)-1)))
endif

EXAMIDLISTEXIST := $(patsubst $(EXAMOUT)/%.pdf,%,$(patsubst %-book.pdf,%.pdf,$(wildcard $(EXAMOUT)/E*.pdf)))
EXAMIDLISTSTEM := $(sort $(EXAMIDLIST:%=E%) $(EXAMIDLISTEXIST))

.PHONY: examids
examids: $(EXAMIDLISTSTEM) ## all exams with id (make EXAMCOUNT=10 examids). Individual exams can be build with Exxxx.

SOLUTIONIDLISTEXIST := $(patsubst $(SOLUTIONOUT)/%.pdf,%,$(wildcard $(SOLUTIONOUT)/E*.pdf))
SOLUTIONIDLISTSTEM := $(sort $(EXAMIDLIST:%=E%-solution) $(SOLUTIONIDLISTEXIST))

.PHONY: solutionids
solutionids: $(SOLUTIONIDLISTSTEM) ## all exams with id (make EXAMCOUNT=10 examids). Individual exams can be build with Exxxx.


# -------------
# Print targets
# -------------

TEXPRINTSRC := $(filter-out tumexam/binder.tex,$(wildcard tumexam/*.tex))
TEXPRINTPDF := $(patsubst tumexam/%.tex,print/%.pdf,$(TEXPRINTSRC))
$(TEXPRINTPDF): print/%.pdf: tumexam/%.tex $(wildcard lists/*)
	$(call pdfbuilder,$<,$@,)
SPECIALTEXPDF += $(TEXPRINTPDF)
TEXPRINTSTEM := $(patsubst print/%.pdf,%,$(TEXPRINTPDF))
.PHONY: $(TEXPRINTSTEM)
$(TEXPRINTSTEM): %: print/%.pdf
PRINTSIGNATURE := protocol
$(PRINTSIGNATURE): %: print/%-signature.pdf
SIGNATURESRC += $(PRINTSIGNATURE:%=print/%.pdf)
PRINTA3 := seatplan
$(PRINTA3): %: print/%-a3.pdf
A3SRC += $(PRINTA3:%=print/%.pdf)
.PHONY: print
print: $(TEXPRINTSTEM) ## all stuff to be printed (except exams)
.PHONY: clean_print
clean_print:
	rm -rfv $(addprefix $(BUILDDIR)/,$(TEXPRINTSRC))
	-rmdir $(BUILDDIR)/print/
	-rmdir $(BUILDDIR)/tumexam/
clean: clean_print
.PHONY: cleanall_print
cleanall_print:
	rm -fv $(TEXPRINTPDF)
	rm -fv $(PRINTSIGNATURE:%=print/%-signature.pdf)
	rm -fv $(PRINTA3:%=print/%-a3.pdf)
	rm -dfv print
cleanall: cleanall_print


# ------------
# Scan targets
# ------------

scan/scanconf.yml: $(EXAMSRC) $$(DEPS_$$(EXAM))
	$(call pdfbuilder,$<,$@,scanconf)
	cp $(BUILDDIR)/$(EXAMSRC)/scanconf/scanconf.yml $@
SPECIALTEXPDF += scan/scanconf.yml
scan/problems.csv: $(EXAMEXAMPLEPDF)
	mkdir -p scan
	cp $(BUILDDIR)/$(EXAMSRC)/example/example-problems.csv $@
scan/boxes.csv: $(EXAMEXAMPLEPDF)
	mkdir -p scan
	cp $(BUILDDIR)/$(EXAMSRC)/example/example-boxes.csv $@
scan/problemboxes.csv: $(EXAMEXAMPLEPDF)
	mkdir -p scan
	cp $(BUILDDIR)/$(EXAMSRC)/example/example-problemboxes.csv $@
scan/registrationboxes.csv: $(EXAMEXAMPLEPDF)
	mkdir -p scan
	cp $(BUILDDIR)/$(EXAMSRC)/example/example-registrationboxes.csv $@
scan/protocolpages.csv: print/protocol.pdf
	mkdir -p scan
	cp $(BUILDDIR)/tumexam/protocol.tex/protocol/protocol-pages.csv $@
scan/attendeelistpages.csv: print/attendeelist.pdf
	mkdir -p scan
	cp $(BUILDDIR)/tumexam/attendeelist.tex/attendeelist/attendeelist-pages.csv $@
scan/srids.csv: print/attendeelist.pdf
	mkdir -p scan
	cp $(BUILDDIR)/tumexam/attendeelist.tex/attendeelist/attendeelist-srids.csv $@
.PHONY: scanconf
scanconf: scan/scanconf.yml
.PHONY: scan_exams
scan_exams: scan/problems.csv scan/boxes.csv scan/problemboxes.csv scan/registrationboxes.csv
.PHONY: scan_lists
scan_lists: scan/protocolpages.csv scan/attendeelistpages.csv scan/srids.csv
.PHONY: scan
scan: scan_exams scan_lists scanconf # all stuff needed for scanning
.PHONY: cleanall_scan
cleanall_scan:
	rm -fv $(TEXSCANPDF)
	rm -rv scan/scanconf.yml
	rm -fv scan/problems.csv
	rm -fv scan/boxes.csv
	rm -fv scan/problemboxes.csv
	rm -fv scan/registrationboxes.csv
	rm -fv scan/protocolpages.csv
	rm -fv scan/attendeelistpages.csv
	rm -fv scan/srids.csv
	rm -dfv scan
cleanall: cleanall_scan


# ------------
# Book targets
# ------------

BOOKPDF := $(BOOKSRC:.pdf=-book.pdf)
$(BOOKPDF): %-book.pdf: %.pdf
	pdfjam --paper a3paper --landscape --booklet true --rotateoversize true --outfile $@ $< 2>/dev/null

SMALLBOOKPDF := $(SMALLBOOKSRC:.pdf=-book.pdf)
$(SMALLBOOKPDF): %-book.pdf: %.pdf
	pdfjam --paper a4paper --landscape --booklet true --rotateoversize true --outfile $@ $< 2>/dev/null

SIGNATUREPDF := $(SIGNATURESRC:.pdf=-signature.pdf)
$(SIGNATUREPDF): %-signature.pdf: %.pdf
	pdfjam --paper a3paper --landscape --signature 4 --rotateoversize true --outfile $@ $< 2>/dev/null

A3PDF := $(A3SRC:.pdf=-a3.pdf)
$(A3PDF): %-a3.pdf: %.pdf
	pdfjam --paper a3paper --landscape --nup 2x1 --rotateoversize true --outfile $@ $< 2>/dev/null


# --------------
# Binder targets
# --------------

BINDERSRC := tumexam/binder.tex
BINDERIN := binder-in
BINDEROUT := binder-out
BINDERPDF := $(patsubst $(BINDERIN)/%,$(BINDEROUT)/binder-%.pdf,$(wildcard $(BINDERIN)/*))
SPECIALTEXPDF += $(BINDERPDF)
BINDERSTEM := $(BINDERPDF:$(BINDEROUT)/%.pdf=%)

$(BINDERPDF): $(BINDEROUT)/binder-%.pdf: $(BINDERSRC) $(BINDERIN)/$$*/binder-info.csv $(BINDERIN)/$$*/binder-corrections.csv $(BINDERIN)/$$*/pages.csv $(BINDERIN)/$$*/status.tex
	$(call pdfbuilder,$<,$@,$*)
.PHONY: $(BINDERSTEM)
$(BINDERSTEM): %: $(BINDEROUT)/%.pdf
.PHONY: binder
binder: $(BINDERSTEM) ## all binder pdfs. Individual binder can be build with binder-Exxxx


# --------------------
# Binder lists targets
# --------------------

BINDERLISTSIN := lists-in
BINDERLISTSOUT := lists-out
BINDERLISTSPDF := $(patsubst $(BINDERLISTSIN)/%,$(BINDERLISTSOUT)/%.pdf,$(wildcard $(BINDERLISTSIN)/*))
$(BINDERLISTSPDF): $(BINDERLISTSOUT)/%.pdf: $$(wildcard $$(patsubst %,$(BINDERLISTSIN)/%/*/*,$$*))
	mkdir -p $(BINDERLISTSOUT)
	pdfjam --paper a4paper --outfile $@ $(sort $^)
.PHONY: binder_lists
binder_lists: $(BINDERLISTSPDF) ## binder pdfs of lists

