whole main() {
    whole a = 10;
    real b = 2.5;
    flag ok = yes;

    when (ok) {
        show(a);
    } otherwise {
        show(b);
    }

    give 0;
}
