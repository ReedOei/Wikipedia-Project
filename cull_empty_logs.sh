for dir in $(ls -1 "logs/"); do
    for innerdir in $(ls -1 "logs/$dir/"); do
        for logfile in $(ls -1 "logs/$dir/$innerdir"); do
            charcount=$(wc -c logs/$dir/$innerdir/$logfile | awk '{print $1}')

            if [[ "$charcount" -eq "2" ]]; then
                echo "logs/$dir/$innerdir/$logfile is empty, deleting."
                rm "logs/$dir/$innerdir/$logfile"
            fi
        done
    done
done
