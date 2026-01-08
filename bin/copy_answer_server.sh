copy_answer_data() {
    docker exec -it scriber_zjs_demo_pg psql -p 5432 -U postgres -d scriber -c "COPY (SELECT answer.data FROM answer WHERE answer.qid = $1 and answer.result = 1 and answer.standard = 1) TO '/tmp/$1.txt'"
    docker cp scriber_zjs_demo_pg:/tmp/$1.txt ./
#    docker exec -it scriber_zjs_demo_pg psql -p 5432 -U postgres -d scriber -c "select pdfinsight from file where file.id = $1"
}

for question_id in $(cat "$1")
do
    copy_answer_data $question_id
done
